# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What a number a chart drew is made of.

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
    drawn_measures,
    grain_step,
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

# a bucket standing for the rows that carry no date at all
NO_DATE = (None, None)

# one page of a rows level, and the stride its paging moves in
PAGE_SIZE = 100

# a breakdown answers "which group explains this" or "how did this move", and
# either stops being readable long before a page of rows does
BREAKDOWN_SIZE = 20

DIMENSION_TYPES = ("String", "Date", "Datetime", "Time")

# the column types a page of rows can be ranked by. A measure over anything
# else, a count of names or an expression that names no column at all, leaves
# no row that is the biggest one
RANKABLE_TYPES = ("Integer", "Decimal")

# the column types a find term can be matched against. A find is a text match,
# and the engine reads a number as text to make one. A date holds no substring a
# reader types, and `like` on one is an error rather than a miss
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
# that reads them can be told apart from anything the surface already carries
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
# the condition holds for, so drilling it carries the condition. The value is
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
    offers before anything is clicked, which is why it comes back with the
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

    `with_operations` adds the pipeline the level was cut as, which an
    authoring surface opens as a query of its own (`_as_opened`). The rows are
    still read here, under `runs_as`: a pipeline run anywhere else runs as its
    caller. It is off by default because a view must never receive the
    pipeline.

    `row_filters`, `sort`, `find` and `page` are how a caller that never receives
    the pipeline reads the rows anyway. They apply to a rows level only, inside
    the same cut, so `total_row_count` counts what the filters and the find left
    and the page is a page of that. A breakdown level is one page by
    construction and takes none of them.
    """
    check_rows(chart)
    _checked_stack(drill_stack)
    _check_drawn_from(chart, drill_stack)
    adhoc_filters = _card_filters_out(adhoc_filters, chart)

    operations, index = _pipeline(chart, drill_stack, operations)
    step = operations[index]
    sliced = operations[:index]

    with runs_as(chart), read_on(_drawn_on(drill_stack)):
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
            drilled = _rows_reading(segment, drill_stack, step, surface, sort, find, row_filters)
            page = _page(page)

        query = chart.get_query(operations=drilled)

        # a breakdown level is fetched once and then kept by the dialog for as
        # long as it is open, so back and crumb pops never come here. A rows
        # level comes back whenever the reader sorts, finds or turns a page
        result = query.execute(adhoc_filters=adhoc_filters, page=page, page_size=page_size, force=True)
        # read before the count builds again, for the reader at the keyboard
        # only, as `InsightsChartv3.fetch` reads the card's
        scope = user_permissions.scope(frappe.session.user)
        # the dialog shows one page and says so: "100 of 1,240" needs the 1,240
        total_row_count = query.count_rows(adhoc_filters=adhoc_filters, force=True)

        ordered = bool(breakdown and breakdown["ordered"])

        response = {
            "columns": result["columns"],
            # the page of a series was taken from its recent end, and a series reads
            # forwards
            "rows": list(reversed(result["rows"])) if ordered else result["rows"],
            "total_row_count": total_row_count,
            # what the client draws this answer by, said outright rather than left
            # to be inferred from a column type: which way the rows run, the grain
            # they were grouped by, and whether they add up to the segment above
            "ordered": ordered,
            "granularity": breakdown["granularity"] if breakdown else None,
            "additive": bool(breakdown and breakdown["additive"]),
            "time_taken": result["time_taken"],
            "executed_at": frappe.utils.now(),
            # what of the reader's own narrowed the cells the level draws, in the
            # keys a card carries it under
            **scope,
        }

        links = record_links(sliced, result["columns"]) if action["type"] == ROWS else {}
        if links:
            response["record_links"] = links

        if with_operations:
            response["operations"] = _as_opened(chart, drilled, adhoc_filters)

        return response


def _as_opened(chart, drilled: list[dict], adhoc_filters: dict | None) -> list[dict]:
    """The level as a query of its own, holding the rows the dialog showed.

    That query runs on the day it is opened and under no dashboard, so both go
    into its steps: every span it tests fixed to the dates it was read as, and
    the dashboard's filters on the chart's query as a step after that query.
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
    """The rows behind the segment, as a file rather than as a page.

    The same cut `drill_data` reads, at the same filters, the same sort and the
    same find and without the page: one pipeline, two ways of taking it away, so
    the file cannot hold rows the dialog would not draw. Whether this caller may
    have a file at all is the endpoint's question, not this one's.
    """
    check_rows(chart)
    _checked_stack(drill_stack)
    _check_drawn_from(chart, drill_stack)
    if _action(drill_stack[-1])["type"] != ROWS:
        frappe.throw(_("Only the rows behind a segment can be exported"))

    adhoc_filters = _card_filters_out(adhoc_filters, chart)
    operations, index = _pipeline(chart, drill_stack, operations)
    step = operations[index]
    sliced = operations[:index]

    with runs_as(chart), read_on(_drawn_on(drill_stack)):
        surface = _surface(chart, operations, index)
        segment = [*sliced, _filter_group(_segment_filters(chart, sliced, drill_stack, step, surface))]
        drilled = _rows_reading(segment, drill_stack, step, surface, sort, find, row_filters)

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
    """The values a reader's own filter on a rows level offers.

    Read off the cut the filter narrows, so the list never offers a value that
    would leave the page empty. `row_filters` is the reader's other rules: a
    rule on this column would have narrowed the list to the value it already
    holds, so the caller leaves it out.
    """
    adhoc_filters = _card_filters_out(adhoc_filters, chart)
    with runs_as(chart), read_on(_drawn_on(drill_stack)):
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
    """The smallest and largest a column of the cut goes, narrowed as the values are."""
    adhoc_filters = _card_filters_out(adhoc_filters, chart)
    with runs_as(chart), read_on(_drawn_on(drill_stack)):
        surface, narrowed = _reader_cut(chart, drill_stack, row_filters, operations)
        on_surface = _surface_column(column, surface)

        return chart.get_query(operations=narrowed).column_range(
            on_surface["name"], adhoc_filters=adhoc_filters
        )


def _reader_cut(
    chart, drill_stack: list, row_filters: list | None, operations: list[dict] | None = None
) -> tuple[list[dict], list[dict]]:
    """The rows a reader is looking at, and the surface they are bounded by.

    What a filter's own offer is read against: the segment the stack pins and
    the reader's other rules, without the ranking, the find or the page, none of
    which change which values a column holds.
    """
    check_rows(chart)
    _checked_stack(drill_stack)
    _check_drawn_from(chart, drill_stack)
    operations, index = _pipeline(chart, drill_stack, operations)
    surface = _surface(chart, operations, index)
    sliced = operations[:index]
    segment = [
        *sliced,
        _filter_group(_segment_filters(chart, sliced, drill_stack, operations[index], surface)),
    ]

    return surface, _narrowed(segment, surface, row_filters)


def check_rows(chart) -> None:
    """Refuse a caller who may have only the chart's picture.

    Here and not at an endpoint: the view and the builder both drill through
    this module, and a gate on one door left the other open.
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


def _check_drawn_from(chart, drill_stack: list) -> None:
    """Refuse a drill from a card drawn off an earlier version of the chart.

    A card keeps its picture until Refresh, and the drill cuts the chart and
    its queries as they are now. A level names the `last_modified` it was drawn
    from; a chart nobody has saved has none to compare.
    """
    drawn = next((level.get("modified") for level in drill_stack if level.get("modified")), None)
    current = chart.last_modified() if drawn else None
    if current and get_datetime(drawn) != get_datetime(current):
        frappe.throw(_("This chart changed. Refresh to drill."), title=_("Chart Changed"))


def _card_filters_out(adhoc_filters: dict | None, chart) -> dict | None:
    """The surface's routed groups, less the card's own.

    A group keyed by the chart is a rule on the card's own columns: the drilled
    row already satisfied it and the segment is its dimension values, so it has
    nothing left to say here.
    """
    return {k: v for k, v in (adhoc_filters or {}).items() if k != chart.name} or None


def _rows_reading(
    segment: list[dict],
    drill_stack: list,
    step: dict,
    surface: list[dict],
    sort: list | None,
    find: str | None,
    row_filters: list | None = None,
) -> list[dict]:
    """A rows level as the reader asked to read it: narrowed, then ranked.

    The filters and the find narrow before anything is ranked, counted or paged,
    so the total the dialog states is the total of what the reader is looking
    at. A sort they named replaces the ranking the click implied: they have said
    which rows they want on the page, which is the whole of what the ranking was
    for.
    """
    narrowed = _narrowed(segment, surface, row_filters)
    if find:
        narrowed = [*narrowed, _find_group(find, surface)]
    ranked = _named_sort(sort, surface) or _rows_order(_clicked(drill_stack[-1]), step, surface)
    return [*narrowed, *ranked]


def _narrowed(segment: list[dict], surface: list[dict], row_filters: list | None) -> list[dict]:
    """The segment, less what the reader's own rules take out of it."""
    rules = _named_filters(row_filters, surface)
    return [*segment, _filter_group(rules)] if rules else list(segment)


def _named_filters(row_filters: list | None, surface: list[dict]) -> list[dict]:
    """The rules the reader wrote, every column of them checked against the surface.

    A rule narrows what the chart already published and can do nothing else, so
    the whole operator set is open — but the column it names is bounded exactly
    as a sort's is: the wire cannot widen what a chart exposes.
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
    """The sort the reader named, every column of it checked against the surface.

    Written back to front: the engine merges chained sorts and the last one it
    is given becomes the primary key, so the reader's first column goes last.
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
    """A find term, matched across every column of the surface that can hold it.

    The exposure bound holds here without a name being checked: the term reaches
    the surface's own columns and nothing else. A hidden column is not drawn, so
    it is not searched either — a row kept by a match the reader cannot see
    reads as a wrong answer.

    A cut with nothing to match against keeps no rows. An empty group is a no-op
    to the engine, so it would keep every one of them instead and the reader
    would read the whole cut as the answer to their term.
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
    """A group no row satisfies, written as a contradiction on a column of the cut."""
    if not surface:
        return _filter_group([])

    column = surface[0]["name"]
    return _filter_group([_rule(column, "is_set", None), _rule(column, "is_not_set", None)])


def _page(page) -> int:
    """Which page of the rows to draw. Anything that is not one is the first."""
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


def _drawn_on(drill_stack: list) -> str | None:
    """The day the card was read, which every level of the stack carries.

    A span is stored unresolved, so read against the day of the click it cuts
    the bucket the reader clicked down to its overlap with a stretch the card
    never counted - in the chart's operations, in the dashboard's filters and in
    the source query alike.
    """
    return next((level.get("drawn_on") for level in drill_stack if level.get("drawn_on")), None)


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
    that carries an order of its own is shown in that order. One that carries
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
    # groups the measure ranks equal come back in whatever order the engine
    # picks, so a query opened from this level could show them differently.
    # The newest `order_by` is the primary sort, so this one only breaks ties
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

    The client is told, because the answer it receives carries column types and
    not aggregations: nothing in a column of decimals says whether they are
    sums or averages. A level drawn as parts of one whole rests
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
    """A segment the engine named rather than read has nothing to cut the rows by.

    A split cuts its values to a cap and rewrites the tail to `Others`, inside
    the step the drill cuts the pipeline before. So the surface holds no row
    whose column equals `Others`, and filtering by it would draw an empty grid
    with nothing on screen saying why.

    Only that rewrite writes the label, and it is written for one split column
    and only where there was a tail to cut: a chart split by two columns never
    reaches it, and a split of fewer values than the cap leaves the column as
    the rows hold it.

    Two questions, because a column can really hold the string `Others` and be
    cut as well. Whether the split cut a tail is the split's own answer; whether
    the surface holds the label is the surface's. Only "no tail" leaves a cut
    that means what the reader clicked: with a tail, either the label stands
    for rows nothing can find, or it stands for both those and the real ones at
    once, and `= Others` would answer with part of the bar and print its count
    as the whole.
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
                "This series holds the rows whose {0} is {1} together with the values the chart did not draw, and nothing cuts exactly those."
            ).format(frappe.bold(dimension.get("column_name")), frappe.bold(PIVOT_OTHERS)),
            title=_("Nothing to Drill Into"),
        )

    frappe.throw(
        _("{0} stands for the values this chart did not draw, so there is nothing behind it.").format(
            frappe.bold(PIVOT_OTHERS)
        ),
        title=_("Nothing to Drill Into"),
    )


def _split_folded_a_tail(chart, sliced: list[dict], step: dict, dimension: dict) -> bool:
    """Whether the split wrote `Others` over a tail, as the engine ran it.

    Asked by building the pipeline through the split rather than read off the
    operation: which values it keeps depends on the rows it saw. Built, never
    executed - the ranking the split does to pick them is what answers.
    """
    chart.get_query(operations=[*sliced, step]).build()
    return folded_a_tail(dimension.get("dimension_name") or dimension.get("column_name"))


def _surface_holds(chart, sliced: list[dict], column: str, value) -> bool:
    """Whether the surface carries a row whose `column` is `value`.

    One row is the whole answer, so the cut is read a page of one. Read without
    the card's own filters: they can only take rows away, and a cut they emptied
    is an honest empty grid rather than a label nobody wrote.
    """
    if not column:
        return False

    query = chart.get_query(operations=[*sliced, _filter_group([_rule(column, "=", value)])])
    return bool(query.execute(page_size=1)["rows"])


def _bucket(on_surface: dict, dimension: dict | None, grains: dict, value) -> tuple | None:
    """The stretch a clicked value stands for, as (start, end), end exclusive.

    Two ways a chart cuts a date into stretches, and a click on either pins the
    whole of the one it landed on. A grain says how long the stretch is and the
    value is where it starts. A span carries its own dates, and the value is
    the day it opens. Anything else stands for itself, and answers with nothing.

    A bucket clicked on no value at all is the rows that carry no date, which
    `NO_DATE` says and `_bucket_filters` matches.
    """
    granularity = _bucket_grain(on_surface, dimension, grains)
    if not granularity:
        return _clicked_window(dimension, value)

    return _grain_bucket(granularity, value, on_surface["type"]) if value else NO_DATE


def _bucket_grain(on_surface: dict, dimension: dict | None, grains: dict) -> str | None:
    """The grain a value on this column stands for a whole bucket of.

    A level above says it outright, and that grain wins: it is the one the reader
    is looking at, whichever the chart underneath happened to draw. Failing that
    the chart's own aggregating operation says it, which is the only answer the first
    level of a stack can have.
    """
    named = grains.get(on_surface["name"])
    if named:
        return _admitted_grain(on_surface, named)

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
    The spans are stored unresolved so that the same chart reads a different
    stretch tomorrow, so they resolve against the day the card was read —
    `drawn_on`, which the card's own answer named and the level carries back.
    A `<unit> to date` span opens on the first of its period and closes on that
    day, so without it the click returns a stretch running to the day of the
    click: rows behind a number that never counted them.

    Both ends move, and only one of them is checked: a label that opens no span
    is refused rather than left to the caller's categorical fallback, and that
    refusal is also what holds a `drawn_on` to a day the card could have been
    read on. The rows are bounded either way — the pipeline underneath carries
    the card's own span filter, which resolves for the same day.
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
    """The measure the click landed on, or every measure the chart draws when it
    landed on none.

    A breakdown draws what was clicked, so a chart with several measures follows
    the one the level names. A number card names none and keeps all of its own.

    Its own is what it draws and not everything it summarizes: a card carries a
    measure for every target and every comparison it reads off its own row, and
    those are the reading's second half rather than readings. Broken down they
    are columns nobody clicked, and one average among them makes the whole level
    non-additive.

    A chart that measures nothing counts rows, the way an axis chart with no
    series does.
    """
    measures = _measures(step)
    measure = _measure_named(clicked, measures)
    return [measure] if measure else _drawn(chart, measures) or [count_of_rows()]


def _drawn(chart, measures: list[dict]) -> list[dict]:
    """The operation's measures the chart draws, in its own order.

    A chart that says nothing about which of its measures it draws draws all of
    them, and so does a pipeline that is not the chart's own: the query builder
    drills the operations it is editing, and no config describes those.
    """
    drawn = {
        m["measure_name"] for m in drawn_measures(chart.chart_type, frappe.parse_json(chart.config or "{}"))
    }
    if not drawn:
        return measures

    return [m for m in measures if m.get("measure_name") in drawn] or measures


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
