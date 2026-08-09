# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The operations a chart runs, derived from its config.

A chart is a source query plus a shape: which columns group it, which measures
it draws, how it is sorted. That shape used to be turned into operations by the
browser and parked in a second query document, so a chart only had rows after
somebody opened it in the builder. Here the shape is turned into operations
wherever the chart runs, from the config alone.

The output is `source + config filters + the chart's own summarize/pivot +
order-by`, in that order. Dashboard filter state is not part of it — that rides
the `adhoc_filters` argument of execution and is applied to the query it names.

Nothing here reads the database or a document: it is a function of chart type,
source query name and config, so the same three inputs always give the same
operations.
"""

import copy

from frappe import _

AXIS_CHARTS = ("Bar", "Line", "Row")
CHART_TYPES = ("Number", *AXIS_CHARTS, "Donut", "Funnel", "Table", "Map", "Bubble", "Sankey")

DEFAULT_MAX_COLUMN_VALUES = 10


def derive_operations(chart_type: str, query: str, config: dict | None) -> list[dict]:
    """The operations JSON this chart executes.

    Call `config_errors` first. Every slot below is read for what it names, so a
    config that has not passed those checks either draws the wrong thing or is
    not a shape this can read at all.
    """
    config = _config_for_derivation(config, chart_type)

    operations = [_source(query)]
    _add_filters(operations, config)
    _add_chart_operation(operations, chart_type, config)
    _add_order_by_from_config(operations, config)
    return operations


def column_granularity(operations: list[dict]) -> dict:
    """The grain each date column was grouped by, so a client can format it.

    The grain lives in the summarize or pivot step. A viewer never receives the
    step itself, so this map is what it gets instead — one grain per column.
    """
    granularity = {}
    for operation in operations:
        if operation.get("type") == "summarize":
            dimensions = operation.get("dimensions") or []
        elif operation.get("type") == "pivot_wider":
            dimensions = operation.get("rows") or []
        else:
            continue

        for dimension in dimensions:
            if dimension.get("granularity"):
                name = dimension.get("dimension_name") or dimension.get("column_name")
                granularity[name] = dimension["granularity"]

    return granularity


def config_errors(chart_type: str, query: str, config: dict | None) -> list[str]:
    """Why this chart cannot be drawn, empty when it can.

    Everything a shape needs to name a column: no query, no chart type, a slot
    holding something that names nothing, or a slot the chart type reads and the
    config leaves empty.
    """
    errors = []

    if not query:
        errors.append(_("Query is required"))
    if not chart_type:
        errors.append(_("Chart type is required"))
    if chart_type not in CHART_TYPES:
        errors.append(_("Invalid chart type: {0}").format(chart_type))

    # a slot of the wrong kind is read no further: every check below reads slots
    # for what they name, which is only possible once they are the right kind
    malformed = _malformed_slots(config)
    if malformed:
        return errors + malformed

    config = _config_for_derivation(config, chart_type)

    if chart_type in AXIS_CHARTS:
        x_axis = config.get("x_axis") or {}
        dimension = x_axis.get("dimension") or {}
        split_by = (config.get("split_by") or {}).get("dimension") or {}
        if not dimension.get("column_name"):
            errors.append(_("X-axis is required"))
        if dimension.get("column_name") == split_by.get("column_name"):
            errors.append(_("X-axis and Split by cannot be the same"))

    if chart_type == "Number":
        if not _named_measures(config.get("number_columns")):
            errors.append(_("Number column is required"))

    if chart_type == "Donut":
        if not (config.get("label_column") or {}).get("column_name"):
            errors.append(_("Label column is required"))
        if not (config.get("value_column") or {}).get("measure_name"):
            errors.append(_("Value column is required"))

    if chart_type == "Funnel":
        # measures mode needs one measure, grouped mode needs a label and a value
        has_measures = any((m or {}).get("measure_name") for m in config.get("measures") or [])
        has_label = (config.get("label_column") or {}).get("column_name")
        has_value = (config.get("value_column") or {}).get("measure_name")
        if not has_measures and not (has_label and has_value):
            errors.append(_("Add a measure, or set a label and value column"))

    if chart_type == "Table":
        if not _named_dimensions(config.get("rows")):
            errors.append(_("Rows are required"))

    if chart_type == "Map":
        if not (config.get("location_column") or {}).get("column_name"):
            errors.append(_("Location column is required"))
        if not (config.get("value_column") or {}).get("measure_name"):
            errors.append(_("Value column is required"))

    if chart_type == "Bubble":
        if not (config.get("xAxis") or {}).get("measure_name"):
            errors.append(_("X-axis is required"))
        if not (config.get("yAxis") or {}).get("measure_name"):
            errors.append(_("Y-axis is required"))

    if chart_type == "Sankey":
        if not (config.get("source_column") or {}).get("column_name"):
            errors.append(_("Source column is required"))
        if not (config.get("target_column") or {}).get("column_name"):
            errors.append(_("Target column is required"))
        if not (config.get("value_column") or {}).get("measure_name"):
            errors.append(_("Value column is required"))

    return errors


# the shape, per chart type


def _add_chart_operation(operations: list[dict], chart_type: str, config: dict):
    if chart_type in AXIS_CHARTS:
        _add_axis_operation(operations, config)
    elif chart_type == "Number":
        _add_number_operation(operations, config)
    elif chart_type == "Donut":
        _add_donut_operation(operations, config)
    elif chart_type == "Funnel":
        _add_funnel_operation(operations, config)
    elif chart_type == "Table":
        _add_table_operation(operations, config)
    elif chart_type == "Map":
        _add_map_operation(operations, config)
    elif chart_type == "Bubble":
        _add_bubble_operation(operations, config)
    elif chart_type == "Sankey":
        _add_sankey_operation(operations, config)


def _add_axis_operation(operations: list[dict], config: dict):
    series = (config.get("y_axis") or {}).get("series") or []
    values = _named_measures(s.get("measure") for s in series) or [count_of_rows()]

    x_dimension = (config.get("x_axis") or {}).get("dimension") or {}
    split_by = (config.get("split_by") or {}).get("dimension") or {}

    if split_by.get("column_name"):
        operations.append(
            _pivot_wider(
                rows=[x_dimension],
                columns=[split_by],
                values=values,
                max_column_values=(config.get("split_by") or {}).get("max_split_values")
                or DEFAULT_MAX_COLUMN_VALUES,
            )
        )
        return

    operations.append(_summarize(measures=values, dimensions=[x_dimension]))


def _add_number_operation(operations: list[dict], config: dict):
    date_column = config.get("date_column") or {}
    operations.append(
        _summarize(
            measures=_named_measures(config.get("number_columns")),
            dimensions=[date_column] if date_column.get("column_name") else [],
        )
    )


def _add_donut_operation(operations: list[dict], config: dict):
    value_column = config.get("value_column") or {}
    operations.append(_summarize(measures=[value_column], dimensions=[config.get("label_column") or {}]))
    _add_order_by(operations, value_column.get("measure_name"), "desc")


def _add_funnel_operation(operations: list[dict], config: dict):
    # measures mode: every measure is a stage, aggregated over the whole result
    # with no group-by, so one row carries them all
    measures = _named_measures(config.get("measures"))
    if measures:
        operations.append(_summarize(measures=measures, dimensions=[]))
        return

    # grouped mode: one row per stage, biggest first
    value_column = config.get("value_column") or {}
    label_column = config.get("label_column") or {}
    if not value_column.get("measure_name") or not label_column.get("column_name"):
        return

    operations.append(_summarize(measures=[value_column], dimensions=[label_column]))
    _add_order_by(operations, value_column.get("measure_name"), "desc")


def _add_table_operation(operations: list[dict], config: dict):
    rows = _named_dimensions(config.get("rows"))
    columns = _named_dimensions(config.get("columns"))
    values = _named_measures(config.get("values"))

    if columns:
        operations.append(
            _pivot_wider(
                rows=rows,
                columns=columns,
                values=values,
                max_column_values=config.get("max_column_values") or DEFAULT_MAX_COLUMN_VALUES,
            )
        )
        return

    operations.append(_summarize(measures=values, dimensions=rows))


def _add_map_operation(operations: list[dict], config: dict):
    operations.append(
        _summarize(
            measures=[config.get("value_column") or {}],
            dimensions=[config.get("location_column") or {}],
        )
    )


def _add_sankey_operation(operations: list[dict], config: dict):
    # a link is one row per source and target, so the two of them group it
    operations.append(
        _summarize(
            measures=[config.get("value_column") or {}],
            dimensions=[config.get("source_column") or {}, config.get("target_column") or {}],
        )
    )


def _add_bubble_operation(operations: list[dict], config: dict):
    measures = _named_measures([config.get("xAxis"), config.get("yAxis"), config.get("size_column")])
    dimensions = _named_dimensions([config.get("dimension"), config.get("quadrant_column")])
    operations.append(_summarize(measures=measures, dimensions=dimensions))


# operations


def _source(query: str) -> dict:
    # `workbook` is carried by the reference but never read to resolve it: a
    # query name is unique on the site. The shipped format writes 0 here.
    return {"type": "source", "table": {"type": "query", "workbook": "", "query_name": query}}


def _summarize(measures: list[dict], dimensions: list[dict]) -> dict:
    return {"type": "summarize", "measures": measures, "dimensions": dimensions}


def _pivot_wider(rows, columns, values, max_column_values) -> dict:
    return {
        "type": "pivot_wider",
        "rows": rows,
        "columns": columns,
        "values": values,
        "max_column_values": max_column_values,
    }


def _order_by(column_name: str, direction: str) -> dict:
    return {
        "type": "order_by",
        "column": {"type": "column", "column_name": column_name},
        "direction": direction,
    }


def count_of_rows() -> dict:
    """The measure a chart draws when it declares none of its own."""
    return {
        "column_name": "count",
        "data_type": "Integer",
        "aggregation": "count",
        "measure_name": "count_of_rows",
    }


def _add_filters(operations: list[dict], config: dict):
    filters = config.get("filters") or {}
    if not filters.get("filters"):
        return
    operations.append({"type": "filter_group", **filters})


def _add_order_by_from_config(operations: list[dict], config: dict):
    for sort in config.get("order_by") or []:
        column_name = (sort.get("column") or {}).get("column_name")
        if column_name and sort.get("direction"):
            _add_order_by(operations, column_name, sort["direction"])


def _add_order_by(operations: list[dict], column_name: str, direction: str):
    """One sort per column, last one wins.

    Donut and Funnel sort by their measure before the config's own sorts are
    read, so a chart sorted on that same measure must move the sort rather than
    add a second one — two order-by steps on one column would fight.
    """
    if not column_name:
        return

    for index, operation in enumerate(operations):
        if operation["type"] != "order_by":
            continue
        if operation["column"]["column_name"] != column_name:
            continue
        if operation["direction"] != direction:
            operations[index] = _order_by(column_name, direction)
        return

    operations.append(_order_by(column_name, direction))


# config


def _config_for_derivation(config: dict | None, chart_type: str) -> dict:
    """The config as derivation reads it, whatever version wrote it.

    Old configs are missing slots and carry older shapes for the axes. The
    builder repairs them on load, so a config that never went through a recent
    builder session still has to derive the same operations here.
    """
    config = _older_shapes_repaired(copy.deepcopy(config) if config else {})

    for dimension in [
        (config.get("x_axis") or {}).get("dimension"),
        (config.get("split_by") or {}).get("dimension"),
        config.get("date_column"),
        config.get("label_column"),
        *(config.get("rows") or []),
        *(config.get("columns") or []),
    ]:
        if isinstance(dimension, dict) and not dimension.get("dimension_name"):
            if dimension.get("column_name"):
                dimension["dimension_name"] = dimension["column_name"]

    return config


def _older_shapes_repaired(config: dict) -> dict:
    """The slots an older release wrote differently, in today's shape.

    A slot holding something no repair understands is left as it is, for
    `config_errors` to report.
    """
    if config.get("x_axis"):
        config["x_axis"] = _axis_with_dimension(config["x_axis"])
    if config.get("split_by"):
        config["split_by"] = _axis_with_dimension(config["split_by"])
    if isinstance(config.get("y_axis"), list):
        config["y_axis"] = {"series": [{"measure": measure} for measure in config["y_axis"]]}

    return config


def _axis_with_dimension(axis) -> dict:
    """An axis used to be the dimension itself, before it grew display options."""
    if isinstance(axis, dict) and axis.get("column_name"):
        return {"dimension": axis}
    return axis


# every slot derivation reads, and the kind of thing it must hold to be read: a
# dict names one thing — a column, a measure, a filter group — and a list names
# several, each item naming one. Nested slots are read the same way, one level in.
SLOT_SHAPES = {
    "x_axis": {"dimension": {}},
    "split_by": {"dimension": {}},
    "y_axis": {"series": [{"measure": {}}]},
    "date_column": {},
    "label_column": {},
    "value_column": {},
    "location_column": {},
    "source_column": {},
    "target_column": {},
    "xAxis": {},
    "yAxis": {},
    "size_column": {},
    "dimension": {},
    "quadrant_column": {},
    "filters": {"filters": [{}]},
    "number_columns": [{}],
    "measures": [{}],
    "rows": [{}],
    "columns": [{}],
    "values": [{}],
    "order_by": [{"column": {}}],
}


def _malformed_slots(config: dict | None) -> list[str]:
    """The slots holding something derivation cannot read.

    A slot that holds a bare string where a column belongs names nothing, and no
    repair can make it name something — the chart is misconfigured, the same as
    one with the slot left empty. Reporting it is what lets the checks in
    `config_errors`, and derivation after them, ask a slot what it names.
    """
    if not config:
        return []
    if not isinstance(config, dict):
        return [_("Chart config must be an object")]

    return _slot_errors(_older_shapes_repaired(copy.deepcopy(config)), SLOT_SHAPES, "")


def _slot_errors(value, shape, slot: str) -> list[str]:
    if not value:
        return []

    if isinstance(shape, list):
        if not isinstance(value, list):
            return [_("{0} is malformed").format(slot)]
        return [error for item in value for error in _slot_errors(item, shape[0], slot)]

    if not isinstance(value, dict):
        return [_("{0} is malformed").format(slot)]

    return [
        error
        for key, inner in shape.items()
        for error in _slot_errors(value.get(key), inner, f"{slot}.{key}" if slot else key)
    ]


def _named_measures(measures) -> list[dict]:
    return [m for m in (measures or []) if m and m.get("measure_name")]


def _named_dimensions(dimensions) -> list[dict]:
    return [d for d in (dimensions or []) if d and d.get("column_name")]
