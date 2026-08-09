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
from datetime import date, datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime

from insights.insights.doctype.insights_chart_v3.chart_query import count_of_rows
from insights.insights.doctype.insights_data_source_v3.data_authority import data_authority_of
from insights.insights.doctype.insights_data_source_v3.ibis_utils import get_columns_from_schema

DATA_SOURCE = "Insights Data Source v3"

RECORDS = "records"
BREAKDOWN = "breakdown"

# what a records level shows. The dialog states the bound it draws; real
# pagination waits for someone to hit it
PAGE_SIZE = 100

# what a breakdown holds. The level answers "which slice explains this" or "how
# did this move", and either stops being readable long before a page of rows does
BREAKDOWN_SIZE = 20

# the columns a segment can be broken down by
DIMENSION_TYPES = ("String", "Date", "Datetime", "Time")

# A dimension that carries an order of its own is shown in that order; one that
# carries none is ranked by the measure. Dates and times are the ordered ones —
# a moment has a before and an after, and the question a series answers is how a
# number moved, not which of its slices is biggest.
ORDERED_TYPES = ("Date", "Datetime", "Time")

# how long each grain runs, in seconds
SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY
MONTH = 30 * DAY
QUARTER = 91 * DAY
YEAR = 365 * DAY

# Every grain an ordered column can be grouped by, coarsening, against the
# length the derivation reckons it in. One table does both jobs: it is the
# ladder a derived grain climbs, and it is what a caller-named one is checked
# against. A `Time` has no date part, so the calendar grains cannot apply to it.
#
# The lengths are deliberately approximate — they only decide which rung a span
# lands on, never a bucket boundary, which the engine's calendar owns. A grain
# with no length is one a reader may ask for and the derivation will never pick:
# a second-by-second breakdown reads as noise at any span, sub-day grains say
# nothing about a Date, and which year a business counts by is its own decision
# rather than a consequence of how much time a segment covers.
GRAINS = {
    "Date": {
        "second": None,
        "minute": None,
        "hour": None,
        "day": DAY,
        "week": WEEK,
        "month": MONTH,
        "quarter": QUARTER,
        "year": YEAR,
        "fiscal_year": None,
    },
    "Datetime": {
        "second": None,
        "minute": MINUTE,
        "hour": HOUR,
        "day": DAY,
        "week": WEEK,
        "month": MONTH,
        "quarter": QUARTER,
        "year": YEAR,
        "fiscal_year": None,
    },
    "Time": {"second": SECOND, "minute": MINUTE, "hour": HOUR},
}

# the two ends of the segment a grain is derived from, named so the aggregate
# that reads them can be told apart from anything the surface already carries
SPAN_START = "drill_span_start"
SPAN_END = "drill_span_end"

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
        segment = [*sliced, _filter_group(_segment_filters(drill_stack, step, surface))]
        page_size = PAGE_SIZE
        breakdown = None
        if action["type"] == BREAKDOWN:
            breakdown = _breakdown(chart, segment, action, step, surface, adhoc_filters)
            page_size = BREAKDOWN_SIZE

        drilled = [*segment, *breakdown["operations"]] if breakdown else segment
        query = chart.get_query(operations=drilled)
        # a level is fetched once and then kept by the dialog for as long as it
        # is open, so back and crumb pops never come here. What does come here
        # is a viewer asking what a number is made of right now
        result = query.execute(adhoc_filters=adhoc_filters, page_size=page_size, force=True)
        # the dialog shows one page and says so: "100 of 1,240" needs the 1,240
        total_row_count = query.count_rows(adhoc_filters=adhoc_filters)

    ordered = bool(breakdown and breakdown["ordered"])

    response = {
        "columns": result["columns"],
        # the page of a series was taken from its recent end, and a series reads
        # forwards
        "rows": list(reversed(result["rows"])) if ordered else result["rows"],
        "total_row_count": total_row_count,
        # what the client draws this answer by, said outright rather than left
        # to be inferred from a column type: which way the rows run, and the
        # grain they were grouped by
        "ordered": ordered,
        "granularity": breakdown["granularity"] if breakdown else None,
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
        return {
            "type": BREAKDOWN,
            "dimension": action[BREAKDOWN],
            "measure": action.get("measure"),
            # the grain the level is read at, either because the reader chose it
            # or because a previous answer said so and the caller wrote it back.
            # Said, it outranks the one the segment's own span suggests
            "granularity": action.get("granularity"),
        }

    frappe.throw(_("A drill level asks either for records or for a breakdown by a dimension"))


def _clicked(level: dict) -> str | None:
    """The measure the click landed on, as the level names it."""
    return (level.get("action") or {}).get("measure")


def _breakdown(chart, segment: list[dict], action: dict, step: dict, surface: list[dict], adhoc_filters):
    """Group what is left by one more column of the surface.

    Which order it comes back in is the whole of the level's rule. A dimension
    that carries an order of its own is shown in that order; one that carries
    none is ranked by the measure, biggest first. Ranking a series of months by
    their size reads as noise, and cutting one to a top twenty takes buckets out
    of the middle of it, leaving a timeline full of holes.
    """
    column = _surface_column(action["dimension"], surface)
    measures = _clicked_measures(action["measure"], step)
    ordered = column["type"] in ORDERED_TYPES

    dimension = {
        "column_name": column["name"],
        "dimension_name": column["name"],
        "data_type": column["type"],
    }
    granularity = _granularity(chart, segment, column, action["granularity"], adhoc_filters)
    if granularity:
        dimension["granularity"] = granularity

    summarize = {
        "type": "summarize",
        "measures": measures,
        "dimensions": [dimension],
    }
    # what makes the page the dialog shows the end worth reading rather than an
    # arbitrary slice: the top of the ranking, or the recent end of the series
    order_by = {
        "type": "order_by",
        "column": {
            "type": "column",
            "column_name": column["name"] if ordered else measures[0]["measure_name"],
        },
        "direction": "desc",
    }
    return {"operations": [summarize, order_by], "ordered": ordered, "granularity": granularity}


# the grain an ordered breakdown groups by


def _granularity(chart, segment: list[dict], column: dict, named: str | None, adhoc_filters) -> str | None:
    """The grain this breakdown buckets by: the caller's, or the segment's own.

    A moment grouped by itself is not a grouping — break a Datetime down raw and
    every row lands in its own second — so an ordered dimension always groups by
    one. A caller names it when the reader changes the grain on the level, and
    otherwise it follows the span of the segment being drilled, which is the
    only thing that knows whether it covers ten minutes or ten years.
    """
    if named:
        return _admitted_grain(column, named)

    grains = GRAINS.get(column["type"]) or {}
    if not grains:
        return None

    return _derived_grain(grains, _span_seconds(chart, segment, column, adhoc_filters))


def _admitted_grain(column: dict, granularity: str) -> str:
    """A grain a caller named, checked against the ones the column has."""
    if granularity not in (GRAINS.get(column["type"]) or {}):
        frappe.throw(_("{0} cannot be broken down by {1}").format(column["name"], granularity))

    return granularity


def _derived_grain(grains: dict, seconds: float) -> str:
    """The finest grain whose buckets fit the span into one window.

    Coarsen until they do: a window holds `BREAKDOWN_SIZE` buckets, and a span
    that starts partway through one spills into another. Nothing coarser than
    the ladder's last rung exists, so a span that outgrows it is exactly what
    the window is there for.
    """
    ladder = {grain: length for grain, length in grains.items() if length}

    for grain, length in ladder.items():
        if seconds / length + 1 <= BREAKDOWN_SIZE:
            return grain

    return list(ladder)[-1]


def _span_seconds(chart, segment: list[dict], column: dict, adhoc_filters) -> float:
    """How much time the segment covers.

    One aggregate over the rows the breakdown is about to group — the segment's
    span and not the chart's, so drilling one month of a ten-year series gets a
    grain that fits the month.
    """
    measures = [
        {
            "measure_name": name,
            "column_name": column["name"],
            "aggregation": aggregation,
            "data_type": column["type"],
        }
        for name, aggregation in ((SPAN_START, "min"), (SPAN_END, "max"))
    ]
    query = chart.get_query(
        operations=[*segment, {"type": "summarize", "measures": measures, "dimensions": []}]
    )
    rows = query.execute(adhoc_filters=adhoc_filters, page_size=1, force=True)["rows"]
    ends = rows[0] if rows else {}

    start, end = ends.get(SPAN_START), ends.get(SPAN_END)
    if start is None or end is None:
        return 0

    return abs((_moment(end) - _moment(start)).total_seconds())


def _moment(value) -> datetime:
    """A value read off an ordered column, as one point on a line.

    A `Time` comes back as an offset into a day rather than a moment, which
    subtraction will not mix with the rest — and which day it is offset into
    does not matter to a difference.
    """
    if isinstance(value, timedelta):
        return datetime.min + value
    if isinstance(value, datetime):
        return value
    if isinstance(value, time):
        return datetime.combine(datetime.min, value)
    if isinstance(value, date):
        return datetime.combine(value, time.min)

    return get_datetime(str(value))


# the segment


def _segment_filters(drill_stack: list, step: dict, surface: list[dict]) -> list[dict]:
    """Every level's segment, narrowing the rows one level at a time.

    A level is read against the levels above it as much as against the chart:
    the grains they grouped by travel down the stack, because a value clicked on
    one of their buckets stands for the whole bucket and nothing else records how
    wide that is.
    """
    filters = []
    grains = {}
    for level in drill_stack:
        for rule in level.get("segment_filters") or []:
            filters += _rule_filters(rule, step, surface, grains)
        filters += _measure_condition(_measure_named(_clicked(level), _measures(step)))
        grains.update(_level_grain(level))

    return filters


def _level_grain(level: dict) -> dict:
    """The bucket a level's own breakdown leaves for the levels under it.

    A level that names no grain leaves none: the derivation that picked one runs
    on the answer, not on the stack, and guessing at it here would be a second
    owner of the same calendar. The level below pins the value it was given.
    """
    action = level.get("action") or {}
    dimension, granularity = action.get(BREAKDOWN), action.get("granularity")
    return {dimension: granularity} if dimension and granularity else {}


def _rule_filters(rule: dict, step: dict, surface: list[dict], grains: dict) -> list[dict]:
    """One clicked dimension value, as the pipeline underneath it filters on it."""
    dimension = _dimension_named(rule.get("column"), step)
    column = (dimension or {}).get("column_name") or rule.get("column")
    on_surface = _surface_column(column, surface)

    operator = rule.get("operator") or "="
    if operator not in OPERATORS:
        frappe.throw(_("Operator {0} is not supported").format(operator))

    granularity = _bucket_grain(on_surface, dimension, grains) if operator == "=" else None
    if granularity:
        return _bucket_filters(column, granularity, rule.get("value"))

    return [_rule(column, operator, rule.get("value"))]


def _bucket_grain(on_surface: dict, dimension: dict | None, grains: dict) -> str | None:
    """The grain a value on this column stands for a whole bucket of.

    A level above says it outright, and that grain wins: it is the one the reader
    is looking at, whichever the chart underneath happened to draw. Failing that
    the chart's own aggregating step says it, which is the only answer the first
    level of a stack can have.
    """
    named = grains.get(on_surface["name"])
    if named:
        return _admitted_grain(on_surface, named)

    return dimension["granularity"] if _is_bucket(dimension) else None


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
    return bool(dimension and dimension.get("granularity") and dimension.get("data_type") in ORDERED_TYPES)


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
