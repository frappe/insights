# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What a view of Insights content is allowed to ask for.

The islands mount on a desk page for a user who may hold no Insights role at
all, so these endpoints are plain `frappe.whitelist(allow_guest=True)`: who may
see what is decided by the permission controller through `visibility`, never by
a role check here. A guest reaches only the `Public` level, and reaches it
through the same code path as everyone else.

Every reference goes through `resolve_for_read`, which answers a missing
reference and a denied one identically. Nothing below re-checks the read after
it, and nothing catches its error — either would give the answer away.

Rendering is all these responses carry. Operations, SQL and the query documents
behind a chart never cross this boundary: the client says which chart, the
server decides what runs.
"""

import frappe
from frappe import _

from insights.insights.doctype.insights_chart_v3.chart_drill import (
    asks_for_rows,
    drill_data,
    drill_dimensions,
    drill_rows_export,
    drill_rows_range,
    drill_rows_values,
)
from insights.insights.doctype.insights_chart_v3.chart_query import config_errors
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
    can_filter_card,
    card_filter_source,
    route_filters,
)
from insights.not_permitted import answers_refusal
from insights.permission_user import runs_as
from insights.permissions import can_copy, can_export, can_read_rows, can_write
from insights.resolver import CHART, DASHBOARD, may_read, not_found, resolve, resolve_for_read

QUERY = "Insights Query v3"


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_dashboard(dashboard: str, surface: str | None = None):
    """A dashboard as a view of it needs: what to lay out, and what it may offer.

    `surface` says which page the view is on, for the `dashboard_viewed` event.
    """
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))
    doc.track_view(surface)
    writable = can_write(doc)
    copyable = can_copy(doc)
    items = frappe.parse_json(doc.items) or []

    # One pass decides which cells reach this reader, and everything below is
    # drawn from it: a cell whose chart is not in `charts` draws "Chart not
    # found", which is not one of the card's states, and the docname it names
    # is the refused content itself - after a workbook is shipped a member's
    # docname is its title in readable form.
    # Whether a grid none of whose charts this reader may read is Not Found is
    # `resolve_for_read`'s to say, once, with its writer exemption.
    charts = charts_on(items)
    readable = {chart.name for chart in charts}

    items = [item for item in items if item.get("type") != "chart" or item.get("chart") in readable]

    return {
        "name": doc.name,
        "route": doc.route,
        "title": doc.title,
        "items": [present_item(item, readable) for item in items],
        # Every chart the grid names, presented as `get_chart` presents one. A
        # cell's height is derived from the config of the chart it draws — a
        # Number card is as tall as its readings make it — so a surface cannot
        # lay the grid out before it holds them, and fetching them per card
        # would reflow the page as each one landed.
        "charts": [present_chart(chart) for chart in charts],
        "vertical_compact_layout": bool(doc.vertical_compact_layout),
        "can_write": writable,
        "can_copy": copyable,
        # where "Edit" lands, and what "Duplicate" copies: the builder is
        # workbook-scoped. It is the one piece of the Builder's structure here, so
        # only a reader who may act on it is told it
        "workbook": doc.workbook if writable or copyable else None,
    }


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_chart(chart: str, dashboard: str | None = None):
    """A chart's rendering config. The query it draws from stays server-side."""
    doc = frappe.get_doc(CHART, resolve_chart(chart, dashboard))

    return {**present_chart(doc), "can_write": can_write(doc)}


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
@answers_refusal(lambda: {"columns": [], "rows": [], "executed_at": frappe.utils.now()})
def get_chart_data(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    force: bool = False,
    page: int = 1,
):
    """A chart's rows, fetched under the permissions the chart declares.

    `filters` is dashboard filter state, keyed by filter name. `card_filters` is
    the reader's own filter on this card: it names a column the card draws, so
    it reaches no further than the picture already does. `page` past the first
    is for a reader `can_read_rows` admits; everyone else gets the chart's one
    page.

    A chart that reads a table or a permlevel column the reader may not read is
    **Not Permitted**: it does not run, and the answer says so and names the
    doctypes it needs.
    """
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return chart_answer(doc, routed_filters(name, dashboard, filters), card_filters, force, page)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_chart_count(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    force: bool = False,
):
    """How many rows the pages of `get_chart_data` are cut from, under the same filters.

    For a reader `can_read_rows` admits. A refusal raises: the card only offers
    the count where the answer it drew said the reader may have it.
    """
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return doc.count_rows(routed_filters(name, dashboard, filters), card_filters, force=force)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def download_chart_rows(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    format: str = "csv",
):
    """Every row the pages of `get_chart_data` are cut from, as a file, under the same filters."""
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return doc.export_rows(format, routed_filters(name, dashboard, filters), card_filters)


def chart_answer(
    doc, adhoc_filters: dict | None, card_filters: list | None, force: bool = False, page: int = 1
) -> dict:
    """A stored chart's picture, as its reader receives it.

    A chart missing a slot says which, as it says it to its author in the
    builder, and runs nothing.
    """
    if errors := config_errors(doc.chart_type, doc.query, frappe.parse_json(doc.config or "{}")):
        return {"errors": errors}

    # before the rows: a query saved while they are read leaves the card an
    # older version than the chart, and the drill refuses instead of cutting it
    chart = present_chart(doc)
    result = doc.fetch(force=force, adhoc_filters=adhoc_filters, card_filters=card_filters, page=page)
    reads_rows = can_read_rows(doc)

    return {
        # the chart these rows were computed from. A card draws the two together,
        # so it never holds a definition its rows do not answer
        "chart": chart,
        "columns": result["columns"],
        "rows": result["rows"],
        "granularity": result["granularity"],
        # a grid draws values, and a value cannot say it names a document. Every
        # chart is asked, and a chart that groups its rows is answered with nothing
        **({"record_links": result["record_links"]} if result.get("record_links") else {}),
        # the series a windowed card's sparkline is drawn from. No other chart
        # carries the key at all
        **({"sparkline": result["sparkline"]} if result.get("sparkline") else {}),
        **({"comparison_rows": result["comparison_rows"]} if result.get("comparison_rows") else {}),
        # what of the reader's own narrowed these rows, so the card can say the
        # number is theirs and not the whole one
        **result["scope"],
        # the drill menu opens on a click, so what it can offer travels with the
        # card instead of costing a round trip at the moment latency is felt
        # `can_rows` rides beside them for the same reason: the menu offers
        # "View rows" and the server decides who may have them, so the answer
        # the menu draws from has to carry both halves
        "drill": {
            "dimensions": drill_dimensions(doc) if reads_rows else [],
            "can_rows": reads_rows,
        },
        # whether the reader may filter the card
        "can_filter": can_filter_card(doc.name),
        # whether the reader may page past the picture and count its rows, and
        # take them away as a file. The card offers each only where it leads
        # somewhere; the endpoints decide
        "can_read_rows": reads_rows,
        "can_export": can_export(doc),
        # the symbol of every currency code these rows carry. A code arrives with
        # the rows it prices, so this is the only thing that fills the client's
        # map - the site is seeded with its own code and nothing else
        "currency_symbols": result["currency_symbols"],
        # the day this card's spans resolved against, so a drill is cut for the
        # day the number was read
        "drawn_on": result["drawn_on"],
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
    }


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
@answers_refusal(lambda: {"columns": [], "rows": []})
def get_drill_data(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    drill_stack: list | None = None,
    sort: list | None = None,
    find: str | None = None,
    page: int = 1,
    row_filters: list | None = None,
):
    """What is behind a segment of a chart, one level of the drill at a time.

    `drill_stack` is the path the reader walked: one level per step, each naming
    the segment it clicked as `segment_filters` — dimension values as plain
    (column, operator, literal) triples — and an `action`, either
    `{"rows": true}` or `{"breakdown": column}`, which may also name the
    `measure` the click landed on and, on a breakdown, the `granularity` it is
    read at. The segments accumulate down the stack and the last level's action
    shapes the answer.

    A grain is worth saying even when the reader did not choose it: a click on a
    bucket a breakdown made pins the bucket's first moment, and the level that
    made it is the only place the span it stands for is written down. So a client
    echoes the `granularity` the answer reports back onto the level it answered.

    Which chart is all the request says about the query. The server re-derives
    the chart's operations, cuts them before the step that aggregated the rows,
    and refuses any column that is not on the surface underneath it: the wire
    cannot widen what a chart exposes.

    The answer says how it should be drawn — `ordered`, whether the rows run in
    an order of their own rather than a ranking, and `granularity`, the grain
    they were bucketed by — so a client never has to work either out from a
    column type.

    A rows level is read the way the reader asked for it, and the reading is the
    server's because the pipeline never leaves it. `row_filters` are the reader's
    own rules over the rows, named the way a segment is — (column, operator,
    value) triples against the surface. `sort` names columns of the surface and
    the direction each runs in, the first one primary. `find` is one term,
    matched across the surface's text and number columns. `page` is which page of
    the cut to draw, at the page size the answer's `total_row_count` is counted
    against. All four apply inside the same cut, so a filter narrows the total as
    well as the page. A breakdown level takes none of them.

    A rows level also says whether this reader may take the cut away as a file,
    so the dialog offers the control only where it leads somewhere.

    A refusal is an answer here. `DrillLevelData` carries `not_permitted` and
    `DrillDialog` draws it the way a card draws a refused chart, so the level
    says the reader may not read what is behind it instead of offering a Retry
    that cannot succeed.
    """
    check_can_drill()

    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    answer = drill_data(
        doc,
        drill_stack,
        adhoc_filters=routed_filters(name, dashboard, filters),
        sort=sort,
        find=find,
        page=page,
        row_filters=row_filters,
    )
    if asks_for_rows(drill_stack):
        answer["can_export"] = can_export(doc)

    return answer


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def download_drill_rows(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    drill_stack: list | None = None,
    sort: list | None = None,
    find: str | None = None,
    format: str = "csv",
    row_filters: list | None = None,
):
    """The rows behind a segment as a file, at the reader's own filters, sort and find.

    The same cut `get_drill_data` draws a page of, taken whole up to the row cap
    a download carries. The request says no more than that one does: which
    chart, which segments, how to read them.
    """
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)
    if not can_export(doc):
        frappe.throw(_("You are not allowed to download data"), exc=frappe.PermissionError)

    return drill_rows_export(
        doc,
        drill_stack,
        adhoc_filters=routed_filters(name, dashboard, filters),
        sort=sort,
        find=find,
        format=format,
        row_filters=row_filters,
    )


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
@answers_refusal(list)
def get_drill_rows_values(
    chart: str,
    column: str,
    drill_stack: list | None = None,
    dashboard: str | None = None,
    filters: dict | None = None,
    row_filters: list | None = None,
    search_term: str | None = None,
):
    """The values a reader's own filter on a rows level offers.

    Gated like the level itself, and bounded like it: only a column of the
    surface the chart published answers, and the values come off the cut the
    reader is reading rather than off the table underneath it.
    """
    check_can_drill()

    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return drill_rows_values(
        doc,
        drill_stack,
        column,
        search_term=search_term,
        adhoc_filters=routed_filters(name, dashboard, filters),
        row_filters=row_filters,
    )


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
@answers_refusal(lambda: None)
def get_drill_rows_range(
    chart: str,
    column: str,
    drill_stack: list | None = None,
    dashboard: str | None = None,
    filters: dict | None = None,
    row_filters: list | None = None,
):
    """The range a number filter on a rows level offers, bounded as its values are."""
    check_can_drill()

    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return drill_rows_range(
        doc,
        drill_stack,
        column,
        adhoc_filters=routed_filters(name, dashboard, filters),
        row_filters=row_filters,
    )


def check_can_drill():
    """Refuse a guest a look behind a chart it can see.

    A public chart stays a picture, and letting anonymous readers walk the rows
    behind it is a decision to make loudly, not one to inherit from the level
    the dashboard sits at.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Sign in to see what is behind this chart"), exc=frappe.PermissionError)


def routed_filters(chart: str, dashboard: str | None, filters: dict | None) -> dict | None:
    """Dashboard filter state, routed to the queries behind one card.

    The links that do the routing name queries and columns, which is exactly
    what a view never receives — so a view sends filter state by name and this
    side turns it into something a query can run.

    A dashboard routes only the charts it carries: a filter's links are not
    checked at save, so one on a dashboard of the caller's own can name any
    chart and any column of its query.
    """
    if not dashboard:
        return None

    resolve_chart(chart, dashboard)
    items = frappe.db.get_value(DASHBOARD, resolve_for_read(DASHBOARD, dashboard), "items")
    return route_filters(items, chart, filters)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
@answers_refusal(list)
def get_filter_values(
    dashboard: str,
    filter_name: str,
    search_term: str | None = None,
    filters: dict | None = None,
):
    """The values a filter on this dashboard offers.

    A view names the filter; the column behind it is looked up here, because the
    link that names it is exactly what never crosses the boundary. The lookup runs
    under the permissions of the chart the filter is linked to, so the values on
    offer are the ones that user is allowed to see.

    `filters` is the other filters' current state, keyed by filter name — the
    same shape `routed_filters` above turns into a chart's adhoc filters. It goes
    through the same `route_filters`, with this filter left out of its own list:
    narrowing its own offer by what it currently holds would make picking a
    second value impossible.
    """
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))

    def values(chart, query, column):
        adhoc_filters = route_filters(doc.items, chart, filters, exclude_filter=filter_name)
        return query.distinct_column_values(column, search_term=search_term, adhoc_filters=adhoc_filters)

    return doc.lookup_filter(filter_name, values, missing=not_found)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
@answers_refusal(lambda: None)
def get_filter_range(dashboard: str, filter_name: str, filters: dict | None = None):
    """The range a filter on this dashboard offers.

    Looked up and routed the way `get_filter_values` is: the preset ranges a
    picker offers and the values it lists answer the same question about the
    same rows.
    """
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))

    def column_range(chart, query, column):
        adhoc_filters = route_filters(doc.items, chart, filters, exclude_filter=filter_name)
        return query.column_range(column, adhoc_filters=adhoc_filters)

    return doc.lookup_filter(filter_name, column_range, missing=not_found)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
@answers_refusal(list)
def get_card_values(chart: str, column: str, dashboard: str | None = None, search_term: str | None = None):
    """The values a reader's own filter on one card offers.

    Only a column the card draws may be asked about, and a column no source
    column holds (a measure, a column a pivot made) offers nothing. The card's
    own filters narrow the list, so it never offers what the card does not show.
    """
    source = card_source(chart, dashboard, column)
    if not source:
        return []
    doc, query, column_name, card_filters = source

    with runs_as(doc):
        return frappe.get_cached_doc(QUERY, query).distinct_column_values(
            column_name, search_term=search_term, adhoc_filters=card_filters
        )


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
@answers_refusal(lambda: None)
def get_card_range(chart: str, column: str, dashboard: str | None = None):
    """The range a reader's own filter on one card offers, narrowed as `get_card_values` is."""
    source = card_source(chart, dashboard, column)
    if not source:
        return None
    doc, query, column_name, card_filters = source

    with runs_as(doc):
        return frappe.get_cached_doc(QUERY, query).column_range(column_name, adhoc_filters=card_filters)


def card_source(chart: str, dashboard: str | None, column: str):
    """The chart a card filter sits on, and where the filter lands on it.

    Nothing when the column holds no values to offer. A column the card does
    not draw is refused like any other reference the caller may not have.
    """
    doc = frappe.get_doc(CHART, resolve_chart(chart, dashboard))
    query, column_name, card_filters = card_filter_source(doc.name, column)
    if not query:
        not_found()
    if not column_name:
        return None
    return doc, query, column_name, card_filters


def resolve_chart(chart: str, dashboard: str | None) -> str:
    """The chart a reference names, for a user who may read it.

    A chart reached through a dashboard is reached by the dashboard's visibility:
    the controller already grants a dashboard's level to the charts linked to it,
    so the read check below is the whole check. The dashboard must resolve first
    and the chart must really be on it, or the reference answers like any other
    reference the caller may not have.
    """
    if not dashboard:
        return resolve_for_read(CHART, chart)

    dashboard_name = resolve_for_read(DASHBOARD, dashboard)
    name = resolve(CHART, chart)
    if not name or not is_on_dashboard(name, dashboard_name):
        not_found()

    return resolve_for_read(CHART, name)


def is_on_dashboard(chart: str, dashboard: str) -> bool:
    items = frappe.parse_json(frappe.db.get_value(DASHBOARD, dashboard, "items") or "[]")
    return any(item.get("type") == "chart" and item.get("chart") == chart for item in items)


def present_item(item: dict, readable: set[str]) -> dict:
    """One dashboard item, reduced to what a view renders it from.

    `readable` is the charts this reader may read, decided once in
    `get_dashboard`. A name outside it is content this reader was refused, and
    a docname is the content being read as much as a title is.
    """
    presented = {
        "type": item.get("type"),
        "layout": item.get("layout"),
        # what an author arranged for a narrower grid. Absent for most items:
        # a breakpoint nobody arranged is derived from the widest one, client
        # side, where the width that decides it is known
        "layouts": item.get("layouts") or {},
    }

    if item.get("type") == "chart":
        presented["chart"] = item.get("chart")
        # which reading of a Number chart this cell draws, by id. A chart
        # states several and a cell draws one, so the cell is the only place
        # the answer is written down
        presented["reading"] = item.get("reading")
    elif item.get("type") == "text":
        presented["text"] = item.get("text")
    elif item.get("type") == "filter":
        # `links` stays behind: it names the query and the column a filter
        # applies to, and routing a filter is the server's job. Which cards a
        # filter changes is presentation — it decides what refetches and which
        # empty card can blame a filter — so the chart names alone come out.
        presented.update(
            {
                "filter_name": item.get("filter_name"),
                "filter_type": item.get("filter_type"),
                "icon": item.get("icon"),
                "default_operator": item.get("default_operator"),
                "default_value": item.get("default_value"),
                "charts": [
                    chart for chart, link in (item.get("links") or {}).items() if link and chart in readable
                ],
            }
        )

    return presented


def charts_on(items: list[dict]) -> list:
    """Every chart the grid names that this reader may read, once each, in order.

    The dashboard's own level reaches them - the controller grants it to the
    charts linked to the dashboard - but the level is not the whole question: a
    User Permission narrowing the reader to one query refuses a chart over
    another. `may_read` is the one answer to
    "may this reader read this content", and it is what `resolve_chart` asks a
    moment later for the same chart: a title and a rendering config handed over
    here is content the card would then be refused.

    A cell naming a chart that has since been deleted is left out too — the
    layout is wrong, not the read.
    """
    named = dict.fromkeys(item.get("chart") for item in items if item.get("type") == "chart")
    return [
        doc
        for doc in (
            frappe.get_cached_doc(CHART, name) for name in named if name and frappe.db.exists(CHART, name)
        )
        if may_read(doc)
    ]


def present_chart(doc) -> dict:
    """A chart, reduced to what draws its card. The query behind it stays here."""
    return {
        "name": doc.name,
        "title": doc.title,
        "chart_type": doc.chart_type,
        "config": present_config(doc.config),
        # a drill carries it back, and is refused once the chart or a query it
        # reads has moved on
        "modified": doc.last_modified(),
    }


def present_config(config) -> dict:
    """The chart config, minus the parts that describe the data instead of the picture."""
    config = frappe.parse_json(config or "{}")
    config.pop("filters", None)
    return config
