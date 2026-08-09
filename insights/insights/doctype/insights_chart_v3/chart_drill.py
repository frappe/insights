# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What a number a chart drew is made of.

A drill walks back down the chart's own pipeline. The operations derived from a
chart end in the step that turned rows into numbers — a summarize or a pivot —
so a drill cuts the pipeline just before that step and works on the surface
underneath it. That surface is the exposure bound: the same rows the chart
aggregated, never the source tables, and every column a caller names is checked
against it before anything runs.

A caller describes the walk, never the pipeline. One level of the stack is the
segment that was clicked — its dimension values as plain triples — and what it
wants there: the records behind the segment, or a breakdown of it by another
column of the surface. Levels accumulate, so every level's segment narrows the
rows and the last level's action decides the shape of the answer.

Nothing here reads a request. It takes a chart document, and the operations it
builds go straight into a query that is executed and thrown away. `operations`
overrides the ones the chart derives, which is how the query builder drills the
pipeline it is editing: there is no config to derive that from, and the walk is
the same walk either way.
"""

import re

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime

from insights.insights.doctype.insights_chart_v3.chart_query import count_of_rows
from insights.insights.doctype.insights_data_source_v3.data_authority import data_authority_of
from insights.insights.doctype.insights_data_source_v3.ibis_utils import get_columns_from_schema

DATA_SOURCE = "Insights Data Source v3"

RECORDS = "records"
BREAKDOWN = "breakdown"

# what a records level shows and a breakdown level ranks. The dialog states the
# bound it draws; real pagination waits for someone to hit it
PAGE_SIZE = 100

# the columns a segment can be broken down by, and the ones whose values name a
# bucket rather than a moment
DIMENSION_TYPES = ("String", "Date", "Datetime", "Time")
DATE_TYPES = ("Date", "Datetime", "Time")

# A moment grouped by itself is not a grouping: break a Datetime down raw and
# every row lands in its own second. The grains match the ones the config UI
# defaults to, in `frontend/src2/helpers/constants.ts`.
DEFAULT_GRANULARITY = {"Date": "month", "Datetime": "month", "Time": "hour"}

# a filter can only narrow what the surface already exposes, so the whole
# operator set is open; naming one the engine does not have is a caller error
OPERATORS = (
    "=",
    "!=",
    ">",
    "<",
    ">=",
    "<=",
    "in",
    "not_in",
    "is_set",
    "is_not_set",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "between",
    "within",
)

# a measure that counts a condition instead of the whole group: the rows behind
# it are the ones the condition holds for, so drilling it carries the condition
CONDITIONAL_MEASURES = (
    re.compile(r"^count_if\(([^,]+),\s*([^)]+)\)$"),
    re.compile(r"^count_if\(([^,]+)\)$"),
    re.compile(r"^sum_if\(([^,]+),\s*([^)]+)\)$"),
    re.compile(r"^distinct_count_if\(([^,]+),\s*([^)]+)\)$"),
)


def drill_dimensions(chart, operations: list[dict] | None = None) -> list[dict]:
    """The columns a segment of this chart can be broken down by.

    The dimension-typed columns of the pre-summarize surface — what the menu
    offers before anything is clicked, which is why it rides the chart's own
    data response instead of a call of its own.

    A pipeline that aggregates nothing has no surface underneath it, so it
    answers with nothing rather than refusing: asking what a result can be
    broken down by is a fair question even when the answer is "it cannot".
    """
    operations = chart.get_operations() if operations is None else operations
    index = _aggregating_step(operations)
    if index is None:
        return []

    with data_authority_of(chart):
        return _dimensions_on(_surface(chart, operations, index))


def drill_data(
    chart,
    drill_stack: list,
    adhoc_filters: dict | None = None,
    operations: list[dict] | None = None,
    with_operations: bool = False,
) -> dict:
    """The rows behind the segment the stack describes.

    `with_operations` puts the sliced pipeline in the answer, for an authoring
    surface that lifts the level into the query builder. It is off by default
    because the reading surfaces must never receive it, and a default that leaks
    is one forgotten argument away.
    """
    if not drill_stack:
        frappe.throw(_("Nothing to drill into: the drill stack is empty"))
    if not all(isinstance(level, dict) for level in drill_stack):
        frappe.throw(_("A drill level must name its segment and its action"))

    operations, index = _pipeline(chart, operations)
    step = operations[index]
    sliced = operations[:index]

    with data_authority_of(chart):
        surface = _surface(chart, operations, index)

        last = drill_stack[-1]
        action = _action(last)
        drilled = [*sliced, _filter_group(_segment_filters(drill_stack, step, surface))]
        if action["type"] == BREAKDOWN:
            drilled += _breakdown(action["dimension"], _clicked(last), step, surface)

        query = chart.get_query(operations=drilled)
        # a level is fetched once and then kept by the dialog for as long as it
        # is open, so back and crumb pops never come here. What does come here
        # is a viewer asking what a number is made of right now
        result = query.execute(adhoc_filters=adhoc_filters, page_size=PAGE_SIZE, force=True)
        # the dialog shows one page and says so: "100 of 1,240" needs the 1,240
        total_row_count = query.count_rows(adhoc_filters=adhoc_filters)

    response = {
        "columns": result["columns"],
        "rows": result["rows"],
        "total_row_count": total_row_count,
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
    }

    link = _record_link(sliced, result["columns"]) if action["type"] == RECORDS else None
    if link:
        response["record_link"] = link

    if with_operations:
        response["operations"] = drilled

    return response


# the pipeline


def _pipeline(chart, operations: list[dict] | None = None) -> tuple[list[dict], int]:
    """The operations to drill, and where the step that aggregated them sits."""
    operations = chart.get_operations() if operations is None else operations
    index = _aggregating_step(operations)
    if index is None:
        frappe.throw(_("Nothing here aggregates any rows, so there is nothing behind it"))

    return operations, index


def _aggregating_step(operations: list[dict]) -> int | None:
    aggregating = [
        index
        for index, operation in enumerate(operations)
        if operation.get("type") in ("summarize", "pivot_wider")
    ]
    return aggregating[-1] if aggregating else None


def _surface(chart, operations: list[dict], index: int) -> list[dict]:
    """The columns the chart aggregated, read off the sliced pipeline's schema.

    Built, never executed: the shape of a result is known before a row of it is.
    """
    query = chart.get_query(operations=operations[:index])
    return get_columns_from_schema(query.build().schema())


def _dimensions_on(surface: list[dict]) -> list[dict]:
    return [column for column in surface if column["type"] in DIMENSION_TYPES]


def _action(level: dict) -> dict:
    """What this level does with its segment."""
    action = level.get("action") or {}
    if action.get(RECORDS):
        return {"type": RECORDS}
    if action.get(BREAKDOWN):
        return {"type": BREAKDOWN, "dimension": action[BREAKDOWN]}

    frappe.throw(_("A drill level asks either for records or for a breakdown by a dimension"))


def _clicked(level: dict) -> str | None:
    """The measure the click landed on, as the level names it."""
    return (level.get("action") or {}).get("measure")


def _breakdown(dimension: str, clicked: str | None, step: dict, surface: list[dict]) -> list[dict]:
    """Group what is left by one more column of the surface, biggest first."""
    column = _surface_column(dimension, surface)
    measures = _clicked_measures(clicked, step)

    dimension = {
        "column_name": column["name"],
        "dimension_name": column["name"],
        "data_type": column["type"],
    }
    if column["type"] in DEFAULT_GRANULARITY:
        dimension["granularity"] = DEFAULT_GRANULARITY[column["type"]]

    summarize = {
        "type": "summarize",
        "measures": measures,
        "dimensions": [dimension],
    }
    # the ranking is the whole point of the level, and it is also what makes the
    # page the dialog shows the top of the list rather than an arbitrary slice
    order_by = {
        "type": "order_by",
        "column": {"type": "column", "column_name": measures[0]["measure_name"]},
        "direction": "desc",
    }
    return [summarize, order_by]


# the segment


def _segment_filters(drill_stack: list, step: dict, surface: list[dict]) -> list[dict]:
    """Every level's segment, narrowing the rows one level at a time."""
    filters = []
    for level in drill_stack:
        for rule in level.get("segment_filters") or []:
            filters += _rule_filters(rule, step, surface)
        filters += _measure_condition(_measure_named(_clicked(level), _measures(step)))

    return filters


def _rule_filters(rule: dict, step: dict, surface: list[dict]) -> list[dict]:
    """One clicked dimension value, as the pipeline underneath it filters on it."""
    dimension = _dimension_named(rule.get("column"), step)
    column = (dimension or {}).get("column_name") or rule.get("column")
    _surface_column(column, surface)

    operator = rule.get("operator") or "="
    if operator not in OPERATORS:
        frappe.throw(_("Operator {0} is not supported").format(operator))

    if operator == "=" and _is_bucket(dimension):
        return _bucket_filters(column, dimension["granularity"], rule.get("value"))

    return [_rule(column, operator, rule.get("value"))]


def _measure_condition(measure: dict | None) -> list[dict]:
    """What a measure that counts a condition pins, beyond the segment itself.

    Without it the rows behind "Overdue" would be every row of the segment, not
    the overdue ones — the number and the records it is made of would disagree.
    """
    expression = ((measure or {}).get("expression") or {}).get("expression", "").strip()
    for pattern in CONDITIONAL_MEASURES:
        match = pattern.match(expression)
        if match:
            return [{"expression": {"type": "expression", "expression": match.group(1).strip()}}]

    return []


def _bucket_filters(column: str, granularity: str, value) -> list[dict]:
    """A date value the chart grouped by a grain stands for the whole bucket."""
    if not value:
        return [_rule(column, "is_not_set", "")]

    start = get_datetime(value)
    step = {"fiscal_year": {"years": 1}, "quarter": {"months": 3}}.get(granularity) or {f"{granularity}s": 1}
    return [
        _rule(column, ">=", _timestamp(start)),
        _rule(column, "<", _timestamp(add_to_date(start, **step))),
    ]


def _rule(column: str, operator: str, value) -> dict:
    return {
        "column": {"type": "column", "column_name": column},
        "operator": operator,
        "value": value,
    }


def _filter_group(filters: list[dict]) -> dict:
    return {"type": "filter_group", "logical_operator": "And", "filters": filters}


def _timestamp(value) -> str:
    return get_datetime(value).strftime("%Y-%m-%d %H:%M:%S")


def _is_bucket(dimension: dict | None) -> bool:
    return bool(dimension and dimension.get("granularity") and dimension.get("data_type") in DATE_TYPES)


# what the aggregating step named


def _dimension_named(name: str, step: dict) -> dict | None:
    if not name:
        frappe.throw(_("A drill filter must name a column"))

    for dimension in _dimensions(step):
        if name in (dimension.get("dimension_name"), dimension.get("column_name")):
            return dimension

    return None


def _dimensions(step: dict) -> list[dict]:
    if step["type"] == "summarize":
        return step.get("dimensions") or []
    return (step.get("rows") or []) + (step.get("columns") or [])


def _measures(step: dict) -> list[dict]:
    if step["type"] == "summarize":
        return step.get("measures") or []
    return step.get("values") or []


def _clicked_measures(clicked: str | None, step: dict) -> list[dict]:
    """The measure the click landed on, or every measure when it landed on none.

    A breakdown draws what was clicked, so a chart with several measures follows
    the one the level names — a number card names none and keeps them all. A
    chart that measures nothing counts rows, the way an axis chart with no
    series does.
    """
    measures = _measures(step)
    measure = _measure_named(clicked, measures)
    return [measure] if measure else measures or [count_of_rows()]


def _measure_named(name: str | None, measures: list[dict]) -> dict | None:
    return next((m for m in measures if name and m.get("measure_name") == name), None)


def _surface_column(name: str, surface: list[dict]) -> dict:
    """A column of the pre-summarize surface, or a refusal.

    The surface is what the chart's author published. A name that is not on it
    is never guessed at: the wire cannot widen what a chart exposes.
    """
    for column in surface:
        if column["name"] == name:
            return column

    frappe.throw(_("{0} is not a column this chart can be drilled by").format(name or "?"))


# the record behind a row


def _record_link(operations: list[dict], columns: list[dict]) -> dict | None:
    """The desk record a drilled row opens, when the row can name one.

    By convention only: the pipeline starts at a site-DB doctype table and the
    table's `name` column reaches the result unrenamed. Anything else — a
    renamed or dropped `name`, an external source, a union — carries no link at
    all, because a wrong record is worse than no control.
    """
    if not any(column["name"] == "name" for column in columns):
        return None

    table = _base_table(operations, set())
    if not table:
        return None

    data_source, table_name = table
    if not frappe.db.get_value(DATA_SOURCE, data_source, "is_site_db"):
        return None
    if not table_name.startswith("tab"):
        return None

    doctype = table_name[len("tab") :]
    return {"doctype": doctype, "column": "name"} if frappe.db.exists("DocType", doctype) else None


def _base_table(operations: list[dict], seen: set) -> tuple[str, str] | None:
    """The one table this pipeline reads, followed through the queries it is built on."""
    for operation in operations:
        if operation.get("type") in ("union", "sql", "code"):
            return None

    source = next((o for o in operations if o.get("type") == "source"), None)
    table = (source or {}).get("table") or {}

    if table.get("type") == "table":
        return table.get("data_source"), table.get("table_name")

    if table.get("type") != "query" or table.get("query_name") in seen:
        return None

    query = table["query_name"]
    seen.add(query)
    return _base_table(
        frappe.parse_json(frappe.db.get_value("Insights Query v3", query, "operations")) or [], seen
    )
