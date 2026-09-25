# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What a number a chart plotted is made of.

A drill walks back down the chart's own pipeline. The operations derived from a
chart end in the operation that turned rows into numbers, a summarize or a
pivot, so a drill cuts the pipeline just before it and works on the surface
underneath. That surface is the exposure bound: the same rows the chart
aggregated, never the source tables, and every column a caller names is checked
against it before anything runs.

A caller describes the walk, never the pipeline. One level of the stack is the
segment that was clicked, its dimension values as plain triples, and what it
wants there: the rows behind the segment, or a breakdown of it by another
column of the surface. Levels accumulate, so every level's segment narrows the
rows and the last level's action decides the shape of the answer.

Nothing here reads a request. It takes a chart document, and the operations it
builds go straight into a query that is executed and thrown away. `operations`
overrides the ones the chart derives, which is how the query builder drills the
pipeline it is editing: there is no config to derive that from, and the walk is
the same walk either way.
"""

import ast
from datetime import date, datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, get_time

from insights import user_permissions
from insights.insights.doctype.insights_chart_v3.chart_query import (
    ORDERED_TYPES,
    count_of_rows,
    grain_step,
    plotted_measures,
)
from insights.insights.doctype.insights_chart_v3.record_link import record_links
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    ADDITIVE_AGGREGATIONS,
    PIVOT_OTHERS,
    folded_a_tail,
    get_columns_from_schema,
)
from insights.insights.query_builders.sql_functions import read_on, resolve_timespan
from insights.not_permitted import refuse
from insights.permission_user import runs_as
from insights.permissions import can_read_rows

ROWS = "rows"
BREAKDOWN = "breakdown"

# a bucket standing for the rows that have no date at all
NO_DATE = (None, None)

PAGE_SIZE = 100

# a breakdown answers "which group explains this" or "how did this move", and
# either stops being readable long before a page of rows does
BREAKDOWN_SIZE = 20

DIMENSION_TYPES = ("String", "Date", "Datetime", "Time")

# the column types a page of rows can be ranked by. A measure over anything
# else, a count of names or an expression that names no column at all, leaves
# no row that is the biggest one
RANKABLE_TYPES = ("Integer", "Decimal")

# the column types a find term can match. A find is a text match, and the
# engine reads a number as text. `like` on a date is an error, not a miss
FINDABLE_TYPES = ("String", "Integer", "Decimal")

SORT_DIRECTIONS = ("asc", "desc")

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY
MONTH = 30 * DAY
QUARTER = 91 * DAY
YEAR = 365 * DAY

# Every grain an ordered column can be grouped by, coarsest last, against the
# length the derivation reckons it in. One table does both jobs: it is the
# order a derived grain coarsens through, and it is what a caller-named grain is
# checked against. A `Time` has no date part, so the calendar grains cannot
# apply to it.
#
# The lengths are deliberately approximate. They only decide which grain a span
# lands on, never a bucket boundary, which the engine's calendar owns. A grain
# with no length is one a reader may ask for and the derivation will never pick:
# a second-by-second breakdown reads as noise at any span, and which year a
# business counts by is its own decision rather than a consequence of how much
# time a segment covers. A `Date` has no time part, so it lists no sub-day grain
# at all: the engine cannot truncate one to an hour.
GRAINS = {
    "Date": {
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
# that reads them can be told apart from anything the surface already includes
SPAN_START = "drill_span_start"
SPAN_END = "drill_span_end"

# a filter can only narrow what the surface already exposes, so the whole
# operator set is open. Naming one the engine does not have is a caller error
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

# a measure that aggregates under a condition: the rows behind it are the ones
# the condition holds for, so drilling it keeps the condition. The value is
# where the gate sits among the positional arguments, or under `where=`
CONDITION_ARGUMENT = {
    "count_if": 0,
    "sum_if": 0,
    "distinct_count_if": 0,
    "count": 1,
    "sum": 1,
    "avg": 1,
    "median": 1,
    "min": 1,
    "max": 1,
    "distinct_count": 1,
    "group_concat": 2,
}


def drill_dimensions(chart, operations: list[dict] | None = None) -> list[dict]:
    """The columns a segment of this chart can be broken down by.

    The dimension-typed columns of the pre-summarize surface: what the menu
    lists before anything is clicked, which is why it comes back with the
    chart's own data response instead of in a call of its own.

    A pipeline that aggregates nothing has no surface underneath it, so it
    answers with nothing rather than refusing: asking what a result can be
    broken down by is a fair question even when the answer is "it cannot".
    """
    operations = chart.get_operations() if operations is None else operations
    index = _aggregating_step(operations)
    if index is None:
        return []

    with runs_as(chart):
        return _dimensions_on(_surface(chart, operations, index))


def drill_data(
    chart,
    drill_stack: list,
    adhoc_filters: dict | None = None,
    operations: list[dict] | None = None,
    with_operations: bool = False,
    sort: list | None = None,
    find: str | None = None,
    page: int = 1,
    row_filters: list | None = None,
) -> dict:
    """The rows behind the segment the stack describes.

    `with_operations` adds the level's pipeline, so the builder can open it as a
    query (`_as_opened`). The rows are still read here, under `runs_as`, because
    a pipeline run anywhere else runs as its caller. It is off by default
    because a view must never receive the pipeline.

    `row_filters`, `sort`, `find` and `page` let a view read the rows without the
    pipeline. They apply to a rows level only, inside the same cut, so
    `total_row_count` counts the rows they leave. A breakdown level is always
    one page and ignores them.
    """
    check_rows(chart)
    _checked_stack(drill_stack)
    _check_chart_unchanged(chart, drill_stack)
    adhoc_filters = _card_filters_out(adhoc_filters, chart)

    operations, index = _pipeline(chart, drill_stack, operations)
    step = operations[index]
    sliced = operations[:index]

    with runs_as(chart), read_on(_read_on(drill_stack)):
        surface = _surface(chart, operations, index)

        last = drill_stack[-1]
        action = _action(last)
        segment = [*sliced, _filter_group(_segment_filters(chart, sliced, drill_stack, step, surface))]
        page_size = PAGE_SIZE
        breakdown = None
        if action["type"] == BREAKDOWN:
            breakdown = _breakdown(chart, segment, action, step, surface, adhoc_filters)
            page_size = BREAKDOWN_SIZE
            drilled = [*segment, *breakdown["operations"]]
            page = 1
        else:
            drilled = _rows_state(segment, drill_stack, step, surface, sort, find, row_filters)
            page = _page(page)

        query = chart.get_query(operations=drilled)

        # the dialog keeps a breakdown level while it is open, so back and
        # breadcrumb clicks do not fetch it again. A rows level is fetched again
        # on every sort, find and page
        result = query.execute(adhoc_filters=adhoc_filters, page=page, page_size=page_size, force=True)
        # read the scope before `count_rows` builds the query again. It is the
        # session user's scope, as in `InsightsChartv3.fetch`
        scope = user_permissions.scope(frappe.session.user)
        # the dialog shows "100 of 1,240", so it needs the total
        total_row_count = query.count_rows(adhoc_filters=adhoc_filters, force=True)

        ordered = bool(breakdown and breakdown["ordered"])

        response = {
            "columns": result["columns"],
            # a series page is taken from its recent end, but a series reads
            # oldest first
            "rows": list(reversed(result["rows"])) if ordered else result["rows"],
            "total_row_count": total_row_count,
            # the client renders the answer from these, because column types do
            # not say them: the row order, the grain, and whether the rows add up
            # to the segment above
            "ordered": ordered,
            "granularity": breakdown["granularity"] if breakdown else None,
            "additive": bool(breakdown and breakdown["additive"]),
            "time_taken": result["time_taken"],
            "executed_at": frappe.utils.now(),
            # the reader's User Permissions that narrowed these rows, under the
            # keys a card uses
            **scope,
        }

        links = record_links(sliced, result["columns"]) if action["type"] == ROWS else {}
        if links:
            response["record_links"] = links

        if with_operations:
            response["operations"] = _as_opened(chart, drilled, adhoc_filters)

        return response


def _as_opened(chart, drilled: list[dict], adhoc_filters: dict | None) -> list[dict]:
    """The level as a query of its own, returning the rows the dialog showed.

    The opened query runs on a later day and outside the dashboard. So every
    `within` span is fixed to the dates it resolved to, and the dashboard's
    filters on the chart's query become a step after the first one.
    """
    routed = (adhoc_filters or {}).get(chart.query)
    steps = [drilled[0], routed, *drilled[1:]] if routed else drilled
    return [_span_fixed(step) for step in steps]


def _span_fixed(step: dict) -> dict:
    if step.get("type") == "filter_group":
        return {**step, "filters": [_span_fixed(rule) for rule in step.get("filters") or []]}
    # a rule inside a group names no type of its own
    if step.get("type") not in ("filter", None) or step.get("operator") != "within":
        return step

    start, end = resolve_timespan(step["value"])
    return {**step, "operator": "between", "value": [str(start), str(end)]}


def drill_rows_export(
    chart,
    drill_stack: list,
    adhoc_filters: dict | None = None,
    sort: list | None = None,
    find: str | None = None,
    format: str = "csv",
    row_filters: list | None = None,
    operations: list[dict] | None = None,
) -> str:
    """The rows behind the segment, as a file.

    It reads the same cut as `drill_data`, with the same filters, sort and find,
    and no page. So the file cannot hold rows the dialog would not show. The
    endpoint decides whether this caller may export.
    """
    check_rows(chart)
    _checked_stack(drill_stack)
    _check_chart_unchanged(chart, drill_stack)
    if _action(drill_stack[-1])["type"] != ROWS:
        frappe.throw(_("Only the rows behind a segment can be exported"))

    adhoc_filters = _card_filters_out(adhoc_filters, chart)
    operations, index = _pipeline(chart, drill_stack, operations)
    step = operations[index]
    sliced = operations[:index]

    with runs_as(chart), read_on(_read_on(drill_stack)):
        surface = _surface(chart, operations, index)
        segment = [*sliced, _filter_group(_segment_filters(chart, sliced, drill_stack, step, surface))]
        drilled = _rows_state(segment, drill_stack, step, surface, sort, find, row_filters)

        return chart.get_query(operations=drilled).export_rows(format=format, adhoc_filters=adhoc_filters)


def drill_rows_values(
    chart,
    drill_stack: list,
    column: str,
    search_term: str | None = None,
    adhoc_filters: dict | None = None,
    row_filters: list | None = None,
    operations: list[dict] | None = None,
) -> list:
    """The values a reader's filter on a rows level suggests.

    They are read from the cut the filter narrows, so no suggested value leaves
    the page empty. `row_filters` holds the reader's other rules. The caller
    leaves out the rule on this column, because it would narrow the list to the
    value it already holds.
    """
    adhoc_filters = _card_filters_out(adhoc_filters, chart)
    with runs_as(chart), read_on(_read_on(drill_stack)):
        surface, narrowed = _reader_cut(chart, drill_stack, row_filters, operations)
        on_surface = _surface_column(column, surface)

        return chart.get_query(operations=narrowed).distinct_column_values(
            on_surface["name"], search_term=search_term, adhoc_filters=adhoc_filters
        )


def drill_rows_range(
    chart,
    drill_stack: list,
    column: str,
    adhoc_filters: dict | None = None,
    row_filters: list | None = None,
    operations: list[dict] | None = None,
) -> list | None:
    """The minimum and maximum of a column of the cut, narrowed as `drill_rows_values` is."""
    adhoc_filters = _card_filters_out(adhoc_filters, chart)
    with runs_as(chart), read_on(_read_on(drill_stack)):
        surface, narrowed = _reader_cut(chart, drill_stack, row_filters, operations)
        on_surface = _surface_column(column, surface)

        return chart.get_query(operations=narrowed).column_range(
            on_surface["name"], adhoc_filters=adhoc_filters
        )


def _reader_cut(
    chart, drill_stack: list, row_filters: list | None, operations: list[dict] | None = None
) -> tuple[list[dict], list[dict]]:
    """The surface, and the rows a reader is looking at.

    A filter reads its suggestions from these rows: the segment the stack pins,
    narrowed by the reader's other rules. The sort, the find and the page are
    left out.
    """
    check_rows(chart)
    _checked_stack(drill_stack)
    _check_chart_unchanged(chart, drill_stack)
    operations, index = _pipeline(chart, drill_stack, operations)
    surface = _surface(chart, operations, index)
    sliced = operations[:index]
    segment = [
        *sliced,
        _filter_group(_segment_filters(chart, sliced, drill_stack, operations[index], surface)),
    ]

    return surface, _narrowed(segment, surface, row_filters)


def check_rows(chart) -> None:
    """Refuse a caller who may see the chart but not its rows.

    The check is here and not at an endpoint, because the view and the builder
    both drill through this module. A check on one endpoint left the other open.
    """
    if not can_read_rows(chart):
        refuse(message=_("You are not allowed to see what is behind this chart"))


def asks_for_rows(drill_stack: list | None) -> bool:
    """Whether the level this stack ends on asks for the rows behind its segment."""
    last = drill_stack[-1] if drill_stack and isinstance(drill_stack[-1], dict) else {}
    return bool((last.get("action") or {}).get(ROWS))


def _checked_stack(drill_stack: list) -> None:
    if not drill_stack:
        frappe.throw(_("Nothing to drill into: the drill stack is empty"))
    if not all(isinstance(level, dict) for level in drill_stack):
        frappe.throw(_("A drill level must name its segment and its action"))


def _check_chart_unchanged(chart, drill_stack: list) -> None:
    """Refuse a drill from a card rendered from an earlier version of the chart.

    A card keeps its result until Refresh, but the drill reads the chart and its
    queries as they are now. Each level keeps the `last_modified` its card was
    rendered from. A chart that was never saved has no value to compare.
    """
    card_modified = next((level.get("modified") for level in drill_stack if level.get("modified")), None)
    current = chart.last_modified() if card_modified else None
    if current and get_datetime(card_modified) != get_datetime(current):
        frappe.throw(_("This chart changed. Refresh to drill."), title=_("Chart Changed"))


def _card_filters_out(adhoc_filters: dict | None, chart) -> dict | None:
    """The routed filter groups, without the card's own.

    A group keyed by the chart filters the card's own columns. The drilled row
    already matches it, and the segment already pins those dimension values.
    """
    return {k: v for k, v in (adhoc_filters or {}).items() if k != chart.name} or None


def _rows_state(
    segment: list[dict],
    drill_stack: list,
    step: dict,
    surface: list[dict],
    sort: list | None,
    find: str | None,
    row_filters: list | None = None,
) -> list[dict]:
    """A rows level as the reader asked for it: filtered, then sorted.

    The filters and the find apply before the sort, the count and the page, so
    the dialog's total counts what the reader sees. A sort the reader chose
    replaces the order the click implied.
    """
    narrowed = _narrowed(segment, surface, row_filters)
    if find:
        narrowed = [*narrowed, _find_group(find, surface)]
    ranked = _named_sort(sort, surface) or _rows_order(_clicked(drill_stack[-1]), step, surface)
    return [*narrowed, *ranked]


def _narrowed(segment: list[dict], surface: list[dict], row_filters: list | None) -> list[dict]:
    """The segment, filtered by the reader's own rules."""
    rules = _named_filters(row_filters, surface)
    return [*segment, _filter_group(rules)] if rules else list(segment)


def _named_filters(row_filters: list | None, surface: list[dict]) -> list[dict]:
    """The reader's filter rules, each column checked against the surface.

    A rule can only narrow what the chart exposes, so every operator is allowed.
    The column is checked as a sort's is: a request cannot widen what a chart
    exposes.
    """
    rules = []
    for rule in row_filters or []:
        if not isinstance(rule, dict):
            frappe.throw(_("A filter names a column of this chart, an operator and a value"))

        column = _surface_column(rule.get("column"), surface)
        operator = rule.get("operator")
        if operator not in OPERATORS:
            frappe.throw(_("Operator {0} is not supported").format(operator))

        rules.append(_rule(column["name"], operator, rule.get("value")))

    return rules


def _named_sort(sort: list | None, surface: list[dict]) -> list[dict]:
    """The reader's sort, each column checked against the surface.

    Written in reverse: the engine merges chained sorts and makes the last one
    the primary key, so the reader's first column goes last.
    """
    rules = []
    for rule in sort or []:
        if not isinstance(rule, dict):
            frappe.throw(_("A sort names a column of this chart and a direction"))

        column = _surface_column(rule.get("column"), surface)
        direction = rule.get("direction") or "asc"
        if direction not in SORT_DIRECTIONS:
            frappe.throw(_("{0} is not a direction rows can be sorted in").format(direction))

        rules.append(
            {
                "type": "order_by",
                "column": {"type": "column", "column_name": column["name"]},
                "direction": direction,
            }
        )

    return list(reversed(rules))


def _find_group(term: str, surface: list[dict]) -> dict:
    """A find term, matched across every findable column of the surface.

    No column name needs a check, because the term only reaches the surface's
    own columns. A hidden column is not shown, so it is not searched. A row kept
    by a match the reader cannot see looks like a wrong answer.

    With no column to match, the group keeps no rows. The engine treats an empty
    group as no filter, so the reader would take the whole cut as the result.
    """
    searchable = [
        column for column in surface if column["type"] in FINDABLE_TYPES and not column.get("hidden")
    ]
    if not searchable:
        return _matches_nothing(surface)

    return {
        "type": "filter_group",
        "logical_operator": "Or",
        "filters": [_rule(column["name"], "contains", term) for column in searchable],
    }


def _matches_nothing(surface: list[dict]) -> dict:
    """A group no row matches: a contradiction on one column of the cut."""
    if not surface:
        return _filter_group([])

    column = surface[0]["name"]
    return _filter_group([_rule(column, "is_set", None), _rule(column, "is_not_set", None)])


def _page(page) -> int:
    """The page of rows to show. An invalid value means the first page."""
    try:
        return max(1, int(page))
    except (TypeError, ValueError):
        return 1


def _pipeline(chart, drill_stack: list, operations: list[dict] | None = None) -> tuple[list[dict], int]:
    """The operations to drill, and where the operation that aggregated them sits."""
    operations = chart.get_operations() if operations is None else operations
    index = _aggregating_step(operations)
    if index is None:
        frappe.throw(_("Nothing here aggregates any rows, so there is nothing behind it"))

    return operations, index


def _read_on(drill_stack: list) -> str | None:
    """The day the card was read. Every level of the stack keeps it.

    Spans are stored unresolved. Resolved on the day of the click, a span would
    narrow the clicked bucket to a stretch the card never counted. This applies
    to the chart's operations, the dashboard's filters and the source query.
    """
    return next((level.get("read_on") for level in drill_stack if level.get("read_on")), None)


def _aggregating_step(operations: list[dict]) -> int | None:
    aggregating = [
        index
        for index, operation in enumerate(operations)
        if operation.get("type") in ("summarize", "pivot_wider")
    ]
    return aggregating[-1] if aggregating else None


def _surface(chart, operations: list[dict], index: int) -> list[dict]:
    """The columns the chart aggregated, read off the cut pipeline's schema.

    Built, never executed: the shape of a result is known before a row of it is.
    """
    query = chart.get_query(operations=operations[:index])
    return get_columns_from_schema(query.build().schema())


def _dimensions_on(surface: list[dict]) -> list[dict]:
    return [column for column in surface if column["type"] in DIMENSION_TYPES]


def _action(level: dict) -> dict:
    """What this level does with its segment."""
    action = level.get("action") or {}
    if action.get(ROWS):
        return {"type": ROWS}
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

    frappe.throw(_("A drill level asks either for rows or for a breakdown by a dimension"))


def _clicked(level: dict) -> str | None:
    """The measure the click landed on, as the level names it."""
    return (level.get("action") or {}).get("measure")


def _rows_order(clicked: str | None, step: dict, surface: list[dict]) -> list[dict]:
    """Rank a rows level by the number that was clicked.

    One page of the segment is shown, so which rows land on it is the level's
    answer: the ones that made the number biggest, ranked by the column the
    measure aggregated. A click that names no measure follows the chart's first,
    and a measure with nothing rankable underneath it leaves the page in
    whatever order the engine hands it back, as it was before.
    """
    measures = _measures(step)
    measure = _measure_named(clicked, measures) or (measures[0] if measures else None)
    column = (measure or {}).get("column_name")
    rankable = any(c["name"] == column and c["type"] in RANKABLE_TYPES for c in surface)
    if not rankable:
        return []

    return [
        {
            "type": "order_by",
            "column": {"type": "column", "column_name": column},
            "direction": "desc",
        }
    ]


def _breakdown(chart, segment: list[dict], action: dict, step: dict, surface: list[dict], adhoc_filters):
    """Group what is left by one more column of the surface.

    Which order it comes back in is the whole of the level's rule. A dimension
    that has an order of its own is shown in that order. One that has
    none is ranked by the measure, biggest first. Ranking a series of months by
    their size reads as noise, and cutting one to a top twenty takes buckets out
    of the middle of it, leaving gaps in the timeline.
    """
    column = _surface_column(action["dimension"], surface)
    measures = _clicked_measures(action["measure"], step, chart)
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
    # arbitrary page: the top of the ranking, or the recent end of the series
    order_by = {
        "type": "order_by",
        "column": {
            "type": "column",
            "column_name": column["name"] if ordered else measures[0]["measure_name"],
        },
        "direction": "desc",
    }
    # the engine returns groups with equal measures in any order, so a query
    # opened from this level could show them in another order. The newest
    # `order_by` is the primary sort, so this one only breaks ties
    tiebreak = {
        "type": "order_by",
        "column": {"type": "column", "column_name": column["name"]},
        "direction": "asc",
    }
    return {
        "operations": [summarize, order_by] if ordered else [summarize, tiebreak, order_by],
        "ordered": ordered,
        "granularity": granularity,
        "additive": _additive(measures),
    }


def _additive(measures: list[dict]) -> bool:
    """Whether this level's groups add up to the value of the segment above it.

    The client is told, because the answer it receives includes column types and
    not aggregations: nothing in a column of decimals says whether they are
    sums or averages. A level plotted as parts of one whole rests
    on this, and a whole made of averages is wrong with nothing on screen to
    show it.
    """
    return bool(measures) and all(measure.get("aggregation") in ADDITIVE_AGGREGATIONS for measure in measures)


def _granularity(chart, segment: list[dict], column: dict, named: str | None, adhoc_filters) -> str | None:
    """The grain this breakdown groups by: the caller's, or the segment's own.

    A moment grouped by itself is not a grouping (break a Datetime down raw and
    every row lands in its own second), so an ordered dimension always groups by
    one. A caller names it when the reader changes the grain on the level, and
    otherwise it follows the span of the segment being drilled, which is the
    only thing that knows whether it covers ten minutes or ten years.
    """
    if named:
        return _allowed_grain(column, named)

    grains = GRAINS.get(column["type"]) or {}
    if not grains:
        return None

    return _derived_grain(grains, _span_seconds(chart, segment, column, adhoc_filters))


def _allowed_grain(column: dict, granularity: str) -> str:
    """A grain a caller named, checked against the ones the column has."""
    if granularity not in (GRAINS.get(column["type"]) or {}):
        frappe.throw(_("{0} cannot be broken down by {1}").format(column["name"], granularity))

    return granularity


def _derived_grain(grains: dict, seconds: float) -> str:
    """The finest grain whose buckets fit the span into one page.

    Coarsen until they do: a page holds `BREAKDOWN_SIZE` buckets, and a span
    that starts partway through one spills into another. Nothing coarser than
    the last grain exists, so a span that outgrows it is exactly what the page
    is there for.
    """
    ladder = {grain: length for grain, length in grains.items() if length}

    for grain, length in ladder.items():
        if seconds / length + 1 <= BREAKDOWN_SIZE:
            return grain

    return list(ladder)[-1]


def _span_seconds(chart, segment: list[dict], column: dict, adhoc_filters) -> float:
    """How much time the segment covers.

    One aggregate over the rows the breakdown is about to group: the segment's
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
    subtraction will not mix with the rest, and which day it is offset into
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


def _segment_filters(
    chart, sliced: list[dict], drill_stack: list, step: dict, surface: list[dict]
) -> list[dict]:
    """Every level's segment, narrowing the rows one level at a time.

    A level is read against the levels above it as much as against the chart:
    the grains they grouped by apply to every level below, because a value clicked on
    one of their buckets stands for the whole bucket and nothing else says how
    wide that is.
    """
    filters = []
    grains = {}
    for level in drill_stack:
        for rule in level.get("segment_filters") or []:
            filters += _rule_filters(chart, sliced, rule, step, surface, grains)
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


def _rule_filters(
    chart,
    sliced: list[dict],
    rule: dict,
    step: dict,
    surface: list[dict],
    grains: dict,
) -> list[dict]:
    """One clicked dimension value, as the pipeline underneath it filters on it."""
    dimension = _dimension_named(rule.get("column"), step)
    column = (dimension or {}).get("column_name") or rule.get("column")
    on_surface = _surface_column(column, surface)

    operator = rule.get("operator") or "="
    if operator not in OPERATORS:
        frappe.throw(_("Operator {0} is not supported").format(operator))

    if operator == "=":
        _refuse_invented_value(chart, sliced, dimension, step, rule.get("value"))
        bucket = _bucket(on_surface, dimension, grains, rule.get("value"))
        if bucket:
            return _bucket_filters(column, bucket)

    return [_rule(column, operator, rule.get("value"))]


def _refuse_invented_value(chart, sliced: list[dict], dimension: dict | None, step: dict, value) -> None:
    """Refuse a segment value that the engine wrote and the rows do not hold.

    A split keeps its top values and rewrites the tail to `Others`. This happens
    inside the step the drill cuts before. So the surface has no row whose
    column equals `Others`, and a filter on it would show an empty grid with no
    reason given.

    Only that rewrite writes the label. It applies to a single split column,
    and only when there was a tail. A chart split by two columns never rewrites,
    and a split with fewer values than the cap keeps the column as it is.

    A column can hold a real `Others` and also have a tail, so there are two
    checks. The split says whether it had a tail. The surface says whether it
    holds the label. Only a split with no tail means what the reader clicked.
    With a tail, the label stands for rows no filter can find, or for those and
    the real `Others` rows together. `= Others` would then return part of the
    bar and show its count as the whole.
    """
    if value != PIVOT_OTHERS or step.get("type") != "pivot_wider":
        return

    columns = step.get("columns") or []
    if not dimension or len(columns) != 1 or dimension != columns[0]:
        return

    if not _split_folded_a_tail(chart, sliced, step, dimension):
        return

    if _surface_holds(chart, sliced, dimension.get("column_name"), value):
        frappe.throw(
            _(
                "This series combines the rows whose {0} is {1} with the values the chart does not show, so it cannot be drilled into."
            ).format(frappe.bold(dimension.get("column_name")), frappe.bold(PIVOT_OTHERS)),
            title=_("Nothing to Drill Into"),
        )

    frappe.throw(
        _("{0} groups the values this chart does not show, so it cannot be drilled into.").format(
            frappe.bold(PIVOT_OTHERS)
        ),
        title=_("Nothing to Drill Into"),
    )


def _split_folded_a_tail(chart, sliced: list[dict], step: dict, dimension: dict) -> bool:
    """Whether the split rewrote a tail to `Others` when the engine ran it.

    The operation cannot say, because the values the split keeps depend on the
    rows. So the pipeline is built through the split, and building it records
    the answer. It is never executed.
    """
    chart.get_query(operations=[*sliced, step]).build()
    return folded_a_tail(dimension.get("dimension_name") or dimension.get("column_name"))


def _surface_holds(chart, sliced: list[dict], column: str, value) -> bool:
    """Whether the surface has a row whose `column` is `value`.

    One row answers it, so the query reads a page of one. The card's own filters
    are left out. They can only remove rows, and a cut they empty is a true empty
    grid, not a label the engine wrote.
    """
    if not column:
        return False

    query = chart.get_query(operations=[*sliced, _filter_group([_rule(column, "=", value)])])
    return bool(query.execute(page_size=1)["rows"])


def _bucket(on_surface: dict, dimension: dict | None, grains: dict, value) -> tuple | None:
    """The stretch a clicked value stands for, as (start, end), end exclusive.

    Two ways a chart cuts a date into stretches, and a click on either pins the
    whole of the one it landed on. A grain says how long the stretch is and the
    value is where it starts. A span has its own dates, and the value is
    the day it opens. Anything else stands for itself, and answers with nothing.

    A bucket clicked on no value at all is the rows that have no date, which
    `NO_DATE` says and `_bucket_filters` matches.
    """
    granularity = _bucket_grain(on_surface, dimension, grains)
    if not granularity:
        return _clicked_window(dimension, value)

    return _grain_bucket(granularity, value, on_surface["type"]) if value else NO_DATE


def _bucket_grain(on_surface: dict, dimension: dict | None, grains: dict) -> str | None:
    """The grain a value on this column stands for a whole bucket of.

    A level above says it outright, and that grain wins: it is the one the reader
    is looking at, whichever the chart underneath happened to plot. Failing that
    the chart's own aggregating operation says it, which is the only answer the first
    level of a stack can have.
    """
    named = grains.get(on_surface["name"])
    if named:
        return _allowed_grain(on_surface, named)

    return dimension["granularity"] if _is_bucket(dimension) else None


def _grain_bucket(granularity: str, value, data_type: str) -> tuple:
    """The bucket a grain cuts, from the moment it starts at.

    A `Time` is an offset into a day and not a moment: read as one it lands on
    today, and the bucket becomes a stretch of the calendar on a column that has
    no date part. The clock is cut the same way once the value is read as a time
    of day, and a bucket that would run past midnight ends where the day does:
    nothing on a clock is later, so it needs no upper end at all.
    """
    step = grain_step(granularity)
    if data_type != "Time":
        start = get_datetime(value)
        return (start, add_to_date(start, **step))

    start = _moment(get_time(value))
    end = add_to_date(start, **step)
    return (start.time(), end.time() if end.date() == start.date() else None)


def _clicked_window(dimension: dict | None, value) -> tuple | None:
    """The span a value on a span dimension stands for.

    A number card grouped by spans labels each row with the date its span
    opens, so the label names the span and resolving the span gives the end.
    Spans are stored unresolved, so the same chart reads a different stretch
    tomorrow. They resolve against the day the card was read: `read_on`, which
    the card's answer sets and each level sends back. A `<unit> to date` span
    opens on the first of its period and closes on that day. Resolved on the
    day of the click, it would return rows the number never counted.

    Both ends move, but only the start is checked. A label that opens no span
    is refused, not passed to the caller's categorical fallback. That refusal
    also keeps `read_on` to a day the card could have been read on. The rows
    are bounded either way: the pipeline underneath keeps the card's own span
    filter, which resolves for the same day.
    """
    windows = (dimension or {}).get("windows") or []
    if not windows or not value:
        return None

    start = get_datetime(value).date()
    for window in windows:
        opened, closed = resolve_timespan(window)
        if opened == start:
            # a span closes on the last day it covers, and a bound is exclusive
            return (get_datetime(opened), get_datetime(add_to_date(closed, days=1)))

    frappe.throw(
        _("This card reads a different stretch of time now. Open it again to see what is behind it."),
        title=_("The Span Has Moved"),
    )


def _measure_condition(measure: dict | None) -> list[dict]:
    """What a measure that counts a condition pins, beyond the segment itself.

    Without it the rows behind "Overdue" would be every row of the segment, not
    the overdue ones, and the number and the rows it is made of would disagree.
    """
    expression = ((measure or {}).get("expression") or {}).get("expression")
    expression = expression.strip() if isinstance(expression, str) else ""
    return [
        {"expression": {"type": "expression", "expression": condition}}
        for condition in aggregate_conditions(expression)
    ]


def aggregate_conditions(source: str) -> list[str]:
    """The conditions that gate an aggregate, as the rows filter that reproduces them.

    A gate reaches an aggregate two ways, and both can appear at once: as the
    `where` argument, by position or by keyword, and as a `one_if` over the
    aggregated column. An aggregate with `group_by` reads rows outside its
    gate, so no rows filter reproduces it and it pins nothing.
    """
    call = _parse_call(source)
    if call is None:
        return []

    name, positional, keywords = call
    gate_index = CONDITION_ARGUMENT.get(name)
    if gate_index is None or "group_by" in keywords:
        return []

    conditions = []
    gate = keywords.get("where") or (positional[gate_index] if len(positional) > gate_index else None)
    if gate:
        conditions.append(gate)

    if gate_index > 0 and positional:
        inner = _parse_call(positional[0])
        if inner and inner[0] == "one_if" and inner[1]:
            conditions.append(inner[1][0])

    return conditions


def _parse_call(source: str) -> tuple[str, list[str], dict[str, str]] | None:
    """A bare function call as its name, positional arguments and keyword arguments, each as source."""
    try:
        node = ast.parse(source.strip(), mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        return None

    positional = [ast.unparse(arg) for arg in node.args]
    keywords = {kw.arg: ast.unparse(kw.value) for kw in node.keywords if kw.arg}
    return node.func.id, positional, keywords


def _bucket_filters(column: str, bucket: tuple) -> list[dict]:
    """A date value the chart cut into a stretch stands for the whole stretch.

    A stretch with no end is one that runs to the end of what the column can
    hold, and the start is the whole of what there is to say about it.
    """
    start, end = bucket
    if start is None:
        return [_rule(column, "is_not_set", "")]

    filters = [_rule(column, ">=", _timestamp(start))]
    if end is not None:
        filters.append(_rule(column, "<", _timestamp(end)))

    return filters


def _rule(column: str, operator: str, value) -> dict:
    return {
        "column": {"type": "column", "column_name": column},
        "operator": operator,
        "value": value,
    }


def _filter_group(filters: list[dict]) -> dict:
    return {"type": "filter_group", "logical_operator": "And", "filters": filters}


def _timestamp(value) -> str:
    """A bucket end as the engine reads it: a time of day keeps no date."""
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    return get_datetime(value).strftime("%Y-%m-%d %H:%M:%S")


def _is_bucket(dimension: dict | None) -> bool:
    return bool(dimension and dimension.get("granularity") and dimension.get("data_type") in ORDERED_TYPES)


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


def _clicked_measures(clicked: str | None, step: dict, chart) -> list[dict]:
    """The measure the click landed on, or every measure the chart plots when it
    landed on none.

    A breakdown plots what was clicked, so a chart with several measures follows
    the one the level names. A number card names none and keeps all of its own.

    Its own is what it plots and not everything it summarizes: a card includes a
    measure for every target and every comparison it reads off its own row, and
    those are the reading's second half rather than readings. Broken down they
    are columns nobody clicked, and one average among them makes the whole level
    non-additive.

    A chart that measures nothing counts rows, the way an axis chart with no
    series does.
    """
    measures = _measures(step)
    measure = _measure_named(clicked, measures)
    return [measure] if measure else _plotted(chart, measures) or [count_of_rows()]


def _plotted(chart, measures: list[dict]) -> list[dict]:
    """The operation's measures the chart plots, in its own order.

    A chart that says nothing about which of its measures it plots plots all of
    them, and so does a pipeline that is not the chart's own: the query builder
    drills the operations it is editing, and no config describes those.
    """
    plotted = {
        m["measure_name"] for m in plotted_measures(chart.chart_type, frappe.parse_json(chart.config or "{}"))
    }
    if not plotted:
        return measures

    return [m for m in measures if m.get("measure_name") in plotted] or measures


def _measure_named(name: str | None, measures: list[dict]) -> dict | None:
    return next((m for m in measures if name and m.get("measure_name") == name), None)


def _surface_column(name: str, surface: list[dict]) -> dict:
    """A column of the pre-summarize surface, or a refusal.

    The surface is what the chart's author published. A name that is not on it
    is never guessed at: a request cannot widen what a chart exposes.
    """
    for column in surface:
        if column["name"] == name:
            return column

    frappe.throw(_("{0} is not a column this chart can be drilled by").format(name or "?"))
