"""Translate a v2 chart into a v3 chart config.

A v2 chart names its columns by result label - `{"xAxis": "Creation", "yAxis":
["Count of Records"]}`. A v3 config names them as a `Dimension` or a `Measure`,
which carry a data type and, for a measure, an aggregation. The missing piece is
the type of each result column, so every function here takes an optional
`columns` list of `{"name", "type", "role"}` and degrades - with a named gap -
when it is not given.

A v2 query is already grouped, so re-aggregating its result column with `sum`
against the same dimension reproduces the v2 numbers.

Everything in this module is pure: dicts in, dicts out, no database.
"""

import json
from dataclasses import dataclass, field

MEASURE_TYPES = ("Integer", "Decimal")
DATE_TYPES = ("Date", "Datetime", "Time")
TEXT_TYPES = ("String", "Text", "JSON", "Array")

# v2 renders a dashboard on a 20 column grid of 30px rows, v3 on a 20 column
# grid of 52px rows. Only the height needs the correction.
V2_ROW_HEIGHT = 30
V3_ROW_HEIGHT = 52

AXIS_TYPES = ("Line", "Bar", "Row", "Mixed Axis", "Scatter")


@dataclass(frozen=True)
class Gap:
    """Something the translation could not carry over.

    `dropped` separates a chart that produced nothing from one that converted
    with a visible loss.
    """

    kind: str
    source: str
    detail: str
    dropped: bool = False


@dataclass
class TranslatedChart:
    source: str
    title: str
    query: str | None
    chart_type: str | None
    config: dict = field(default_factory=dict)
    gaps: list[Gap] = field(default_factory=list)


class ColumnTypes:
    """The result columns of the query a chart reads.

    v2 labels carry stray whitespace and inconsistent case ("Count of records "
    against "Count of Records"), so lookups fall back to a normalized key.
    """

    def __init__(self, columns: list[dict] | None = None):
        self.columns = columns or []
        self._by_name = {}
        for column in self.columns:
            name = column.get("name") or column.get("label")
            if not name:
                continue
            self._by_name.setdefault(name, column)
            self._by_name.setdefault(_normalize(name), column)

    def __bool__(self):
        return bool(self.columns)

    def knows(self, name: str) -> bool:
        return self._find(name) is not None

    def type_of(self, name: str) -> str | None:
        column = self._find(name)
        return column.get("type") if column else None

    def is_measure(self, name: str) -> bool:
        column = self._find(name)
        if not column:
            return False
        if column.get("role"):
            return column["role"] == "measure"
        return column.get("type") in MEASURE_TYPES

    def is_dimension(self, name: str) -> bool:
        column = self._find(name)
        return bool(column) and not self.is_measure(name)

    def names(self) -> list[str]:
        return [c.get("name") or c.get("label") for c in self.columns if c.get("name") or c.get("label")]

    def dimension(self, name: str) -> dict:
        data_type = self.type_of(name)
        if data_type not in DATE_TYPES:
            data_type = "String"
        return {"dimension_name": name, "column_name": name, "data_type": data_type}

    def measure(self, name: str) -> dict:
        data_type = self.type_of(name)
        if data_type not in MEASURE_TYPES:
            data_type = "Decimal"
        return {
            "measure_name": name,
            "column_name": name,
            "data_type": data_type,
            "aggregation": "sum",
        }

    def _find(self, name):
        if not name:
            return None
        return self._by_name.get(name) or self._by_name.get(_normalize(name))


def _normalize(name: str) -> str:
    return str(name).strip().lower()


def parse_json(value, default=None):
    if isinstance(value, dict | list):
        return value
    if not value:
        return default if default is not None else {}
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return default if default is not None else {}
    return parsed if parsed is not None else (default if default is not None else {})


def chart_from_dashboard_item(item: dict) -> dict:
    """Read a v2 dashboard item as a v2 chart.

    A dashboard item holds its own copy of the chart options, and only 162 of
    1103 production items fill the `query` and `chart` columns - the rest keep
    the query inside `options`.
    """
    options = parse_json(item.get("options"))
    return {
        "name": item.get("name"),
        "chart_type": item.get("item_type"),
        "query": item.get("query") or options.get("query"),
        "options": options,
        "title": item.get("chart_title") or options.get("title"),
    }


def translate_chart(chart: dict, columns: list[dict] | None = None) -> TranslatedChart:
    """Convert one v2 chart into a v3 chart type plus config."""
    options = parse_json(chart.get("options"))
    source = chart.get("name") or ""
    chart_type = chart.get("chart_type")
    title = chart.get("title") or options.get("title") or source
    query = chart.get("query") or options.get("query")

    translated = TranslatedChart(
        source=source,
        title=title,
        query=query,
        chart_type=None,
        config={},
    )

    types = ColumnTypes(columns)
    translator = _TRANSLATORS.get(chart_type)

    if not chart_type:
        # v2 leaves chart_type empty two ways: a chart that was configured before
        # the type existed, and a row for a chart nobody ever visualized
        if not options:
            translated.gaps.append(
                Gap(
                    kind="chart_never_visualized",
                    source=source,
                    detail="the v2 chart has neither a type nor any options",
                    dropped=True,
                )
            )
            return translated
        translator = _translate_auto

    if not translator:
        translated.gaps.append(
            Gap(
                kind="unsupported_chart_type",
                source=source,
                detail=f"v2 chart type {chart_type!r} has no v3 equivalent",
                dropped=True,
            )
        )
        return translated

    translator(translated, options, types)
    if translated.chart_type:
        translated.config.setdefault("order_by", [])
    return translated


def _axis_columns(value) -> list[dict]:
    """Read a v2 axis into `[{"name", "type"}]`.

    An axis is a bare label, a list of labels, or a list of
    `{"column", "series_options": {"type"}}` - all three shapes are in production.
    """
    if not value:
        return []
    if isinstance(value, str):
        return [{"name": value, "type": None}]
    if isinstance(value, dict):
        value = [value]

    axis = []
    for entry in value:
        if isinstance(entry, str):
            axis.append({"name": entry, "type": None})
            continue
        if not isinstance(entry, dict):
            continue
        name = entry.get("column") or entry.get("value") or entry.get("label")
        if not name:
            continue
        series_type = entry.get("type") or (entry.get("series_options") or {}).get("type")
        axis.append({"name": name, "type": series_type})
    return axis


def _int_or_none(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _translate_axis_chart(translated, options, types, chart_type):
    source = translated.source
    x_axis = _axis_columns(options.get("xAxis"))
    y_axis = _axis_columns(options.get("yAxis"))

    # a v2 chart can sit on a dashboard with an axis never chosen; it keeps its
    # type and its place in the layout, and lands unconfigured in v3
    if not x_axis:
        translated.gaps.append(
            Gap("missing_x_axis", source, f"{chart_type} chart has no x axis column in v2")
        )
    if not y_axis:
        translated.gaps.append(
            Gap("missing_y_axis", source, f"{chart_type} chart has no y axis column in v2")
        )

    _warn_unknown_columns(translated, types, [c["name"] for c in x_axis + y_axis])

    default_series_type = "bar" if chart_type in ("Bar", "Row") else "line"
    split = bool(options.get("splitYAxis"))
    series = []
    for index, column in enumerate(y_axis):
        entry = {
            "measure": types.measure(column["name"]),
            "type": column["type"] or default_series_type,
        }
        if split:
            entry["align"] = "Right" if index else "Left"
        series.append(entry)

    x_config = {"dimension": types.dimension(x_axis[0]["name"])} if x_axis else {}
    rotation = _int_or_none(options.get("rotateLabels"))
    if rotation:
        x_config["label_rotation"] = rotation

    y_config = {"series": series}
    if options.get("show_data_labels"):
        y_config["show_data_labels"] = True
    for v2_key, v3_key in (("yAxisMin", "min"), ("yAxisMax", "max")):
        value = _int_or_none(options.get(v2_key))
        if value is not None:
            y_config[v3_key] = value

    if chart_type == "Line":
        if options.get("smoothLines"):
            y_config["smooth"] = True
        if options.get("showPoints"):
            y_config["show_data_points"] = True
        if options.get("showArea"):
            y_config["show_area"] = True
    if chart_type in ("Bar", "Row") and options.get("stack"):
        y_config["stack"] = True

    config = {"x_axis": x_config, "y_axis": y_config}

    # a second x axis column is a split, not a second axis
    if len(x_axis) > 1:
        config["split_by"] = {"dimension": types.dimension(x_axis[1]["name"])}
    if len(x_axis) > 2:
        dropped = ", ".join(c["name"] for c in x_axis[2:])
        translated.gaps.append(
            Gap(
                "extra_x_axis_columns",
                source,
                f"v3 takes one x axis and one split, dropped: {dropped}",
            )
        )

    reference_line = _reference_line(options.get("referenceLine"))
    if reference_line:
        y_config["reference_lines"] = [reference_line]

    translated.config = config
    translated.chart_type = chart_type


V2_REFERENCE_STATISTICS = {"average": "average", "median": "median", "min": "min", "max": "max"}


def _reference_line(value):
    """v2 draws its reference line at a statistic of the plotted data.

    Every production reference line is one of Average, Median, Min or Max -
    v2 hands the lowercased word to an ECharts `markLine` type. v3's
    `ReferenceLine` names the same statistic and computes it off the plotted
    rows, so the word carries over as-is and the line draws where v2 drew it.
    No `value` is written: v3 ignores one whenever a `statistic` is set.
    """
    if isinstance(value, dict):
        value = value.get("value") or value.get("label")
    if not isinstance(value, str):
        return None

    statistic = V2_REFERENCE_STATISTICS.get(value.strip().lower())
    if not statistic:
        return None
    return {"axis": "y", "label": value.strip(), "statistic": statistic}


def _warn_unknown_columns(translated, types, names):
    if not types:
        translated.gaps.append(
            Gap(
                "column_types_unknown",
                translated.source,
                "no result columns given, dimensions assumed String and measures summed",
            )
        )
        return
    unknown = [name for name in names if name and not types.knows(name)]
    if unknown:
        translated.gaps.append(
            Gap(
                "column_not_in_query",
                translated.source,
                f"columns missing from the query result: {', '.join(sorted(set(unknown)))}",
            )
        )


def _translate_line(translated, options, types):
    _translate_axis_chart(translated, options, types, "Line")


def _translate_bar(translated, options, types):
    _translate_axis_chart(translated, options, types, "Bar")


def _translate_row(translated, options, types):
    _translate_axis_chart(translated, options, types, "Row")


def _translate_mixed_axis(translated, options, types):
    """v3 has no mixed type - an axis chart carries the type per series."""
    _translate_axis_chart(translated, options, types, "Line")


def _translate_scatter(translated, options, types):
    """v2 scatter is an axis chart with a categorical x, v3 Bubble needs two measures."""
    x_axis = _axis_columns(options.get("xAxis"))
    x_is_measure = bool(x_axis) and types.is_measure(x_axis[0]["name"])
    if not x_is_measure:
        translated.gaps.append(
            Gap(
                "scatter_x_not_numeric",
                translated.source,
                "v3 Bubble plots a measure against a measure; converted to a line chart instead",
            )
        )
        _translate_axis_chart(translated, options, types, "Line")
        if translated.config:
            translated.config["y_axis"]["show_data_points"] = True
        return

    y_axis = _axis_columns(options.get("yAxis"))
    if not y_axis:
        translated.gaps.append(
            Gap("missing_y_axis", translated.source, "Scatter chart has no y axis column in v2")
        )

    translated.chart_type = "Bubble"
    translated.config = {"xAxis": types.measure(x_axis[0]["name"])}
    if y_axis:
        translated.config["yAxis"] = types.measure(y_axis[0]["name"])
    if len(y_axis) > 1:
        dropped = ", ".join(c["name"] for c in y_axis[1:])
        translated.gaps.append(
            Gap("extra_y_axis_columns", translated.source, f"v3 Bubble plots one measure, dropped: {dropped}")
        )


def _translate_pie(translated, options, types):
    label = _axis_columns(options.get("xAxis"))
    value = _axis_columns(options.get("yAxis"))
    if not label or not value:
        translated.gaps.append(
            Gap("missing_label_or_value", translated.source, "Pie chart has no label or value column in v2")
        )

    _warn_unknown_columns(translated, types, [c[0]["name"] for c in (label, value) if c])
    # v2's own Pie widget drew a donut (radius ['40%', '70%']), so v3's Donut
    # is the same shape under a different name, not a downgrade
    translated.chart_type = "Donut"
    config = {}
    if label:
        config["label_column"] = types.dimension(label[0]["name"])
    if value:
        config["value_column"] = types.measure(value[0]["name"])
    max_slices = _int_or_none(options.get("maxSlices"))
    if max_slices:
        config["max_slices"] = max_slices
    if options.get("inlineLabels"):
        config["show_inline_labels"] = True
    position = options.get("labelPosition")
    if position in ("top", "bottom", "left", "right"):
        config["legend_position"] = position

    translated.config = config


def _translate_funnel(translated, options, types):
    label = _axis_columns(options.get("xAxis"))
    value = _axis_columns(options.get("yAxis"))
    if not label or not value:
        translated.gaps.append(
            Gap(
                "missing_label_or_value",
                translated.source,
                "Funnel chart has no label or value column in v2",
            )
        )
    _warn_unknown_columns(translated, types, [c[0]["name"] for c in (label, value) if c])
    translated.chart_type = "Funnel"
    translated.config = {}
    if label:
        translated.config["label_column"] = types.dimension(label[0]["name"])
    if value:
        translated.config["value_column"] = types.measure(value[0]["name"])


def _number_format_options(options):
    config = {}
    if "shorten" in options:
        config["shorten_numbers"] = bool(options["shorten"])
    decimal = _int_or_none(options.get("decimals"))
    if decimal is not None:
        config["decimal"] = decimal
    for key in ("prefix", "suffix"):
        if options.get(key):
            config[key] = options[key]
    return config


def _translate_number(translated, options, types):
    column = options.get("column")
    if not column:
        y_axis = _axis_columns(options.get("yAxis"))
        column = y_axis[0]["name"] if y_axis else None
    if not column:
        translated.gaps.append(
            Gap("missing_value_column", translated.source, "Number chart has no column in v2")
        )

    _warn_unknown_columns(translated, types, [column])
    translated.chart_type = "Number"
    translated.config = {
        "number_columns": [types.measure(column)] if column else [],
        "number_column_options": [],
        "comparison": False,
        "sparkline": False,
        **_number_format_options(options),
    }


def _translate_trend(translated, options, types):
    """v2 Trend is the current value against the previous one - v3 calls that a comparison."""
    column = options.get("valueColumn") or options.get("column")
    if not column:
        translated.gaps.append(
            Gap("missing_value_column", translated.source, "Trend chart has no value column in v2")
        )

    _warn_unknown_columns(translated, types, [column])
    translated.chart_type = "Number"
    config = {
        "number_columns": [types.measure(column)] if column else [],
        "number_column_options": [],
        "comparison": True,
        "sparkline": bool(options.get("showTrendLine")),
        **_number_format_options(options),
    }
    if options.get("dateColumn"):
        config["date_column"] = types.dimension(options["dateColumn"])
    else:
        translated.gaps.append(
            Gap(
                "trend_without_date_column",
                translated.source,
                "v3 compares over a date column; without one the comparison stays empty",
            )
        )
    if options.get("reverseDelta"):
        config["negative_is_better"] = True

    translated.config = config


def _translate_progress(translated, options, types):
    """v2 Progress is a value against a target - v3 has no progress or gauge chart."""
    column = options.get("progress") or options.get("column")
    if not column:
        translated.gaps.append(
            Gap("missing_value_column", translated.source, "Progress chart has no column in v2")
        )

    _warn_unknown_columns(translated, types, [column])
    translated.chart_type = "Number"
    translated.config = {
        "number_columns": [types.measure(column)] if column else [],
        "number_column_options": [],
        "comparison": False,
        "sparkline": False,
        **_number_format_options(options),
    }
    target = options.get("target")
    translated.gaps.append(
        Gap(
            "progress_target_unsupported",
            translated.source,
            f"v3 has no progress chart; the value survives as a number, the target ({target}) does not",
        )
    )


def _pivot_columns(value) -> list[str]:
    names = []
    for entry in value or []:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict):
            name = entry.get("value") or entry.get("column") or entry.get("label")
            if name:
                names.append(name)
    return names


def _table_flags(translated, options):
    config = {}
    if options.get("showTotal"):
        # v2 shows a totals footer row, which v3 calls the column totals
        config["show_column_totals"] = True
    if options.get("filtersEnabled"):
        config["show_filter_row"] = True
    if options.get("shorten"):
        config["compact_numbers"] = True
    return config


def _split_table_columns(translated, types, names):
    """A v3 table groups by its rows and aggregates its values."""
    _warn_unknown_columns(translated, types, names)
    rows, values = [], []
    for name in names:
        if types and types.is_measure(name):
            values.append(types.measure(name))
        else:
            rows.append(types.dimension(name))
    return rows, values


def _translate_table(translated, options, types):
    names = _pivot_columns(options.get("columns"))
    if not names and types:
        names = types.names()
    if not names:
        translated.gaps.append(
            Gap("missing_columns", translated.source, "Table chart lists no columns in v2")
        )

    rows, values = _split_table_columns(translated, types, names)
    translated.chart_type = "Table"
    translated.config = {"rows": rows, "columns": [], "values": values, **_table_flags(translated, options)}


def _translate_pivot_table(translated, options, types):
    rows = _pivot_columns(options.get("rows"))
    columns = _pivot_columns(options.get("columns"))
    values = _pivot_columns(options.get("values"))
    if not rows and not values:
        translated.gaps.append(
            Gap("missing_columns", translated.source, "Pivot table has no rows or values in v2")
        )

    _warn_unknown_columns(translated, types, rows + columns + values)
    translated.chart_type = "Table"
    translated.config = {
        "rows": [types.dimension(name) for name in rows],
        "columns": [types.dimension(name) for name in columns],
        "values": [types.measure(name) for name in values],
        **_table_flags(translated, options),
    }


def _translate_auto(translated, options, types):
    """v2 picks the type from the result at render time.

    Its last fallback is a table of every column, which is the only branch that
    needs no data, so that is what an `Auto` chart becomes.
    """
    if not types:
        translated.chart_type = "Table"
        translated.config = {"rows": [], "columns": [], "values": []}
        translated.gaps.append(
            Gap(
                "auto_type_needs_columns",
                translated.source,
                "v2 chose the type from the query result; the table lands empty until the "
                "result columns are supplied",
            )
        )
        return

    rows, values = _split_table_columns(translated, types, types.names())
    translated.chart_type = "Table"
    translated.config = {"rows": rows, "columns": [], "values": values}
    translated.gaps.append(
        Gap(
            "auto_type_guessed",
            translated.source,
            "v2 guessed the chart type from the data; converted to a table",
        )
    )


_TRANSLATORS = {
    "Line": _translate_line,
    "Bar": _translate_bar,
    "Row": _translate_row,
    "Mixed Axis": _translate_mixed_axis,
    "Scatter": _translate_scatter,
    "Pie": _translate_pie,
    "Funnel": _translate_funnel,
    "Number": _translate_number,
    "Trend": _translate_trend,
    "Progress": _translate_progress,
    "Table": _translate_table,
    "Pivot Table": _translate_pivot_table,
    "Auto": _translate_auto,
}

SUPPORTED_V2_CHART_TYPES = tuple(_TRANSLATORS)
