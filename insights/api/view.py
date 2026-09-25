# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The endpoints of a View of Insights content.

Islands render on desk pages for users who may hold no Insights role, so these
endpoints are `frappe.whitelist(allow_guest=True)`. The permission controller
decides who reads what through `visibility`; there is no role check here. A
guest reads only `Public` content, through the same code path as everyone else.

Every reference goes through `resolve_for_read`, which answers Not Found for a
missing reference and a refused one alike. Nothing below checks the read again
or catches its error, because either would reveal which case it was.

Responses include only what rendering needs. Operations, SQL and the queries
behind a chart never leave the server: the client names the chart, and the
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


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
def get_dashboard(dashboard: str, surface: str | None = None):
    """A dashboard with what a View needs: its layout, and what the reader may do with it.

    `surface` names the page the View is on, for the `dashboard_viewed` event.
    """
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))
    doc.track_view(surface)
    writable = can_write(doc)
    copyable = can_copy(doc)
    items = frappe.parse_json(doc.items) or []

    # Decide once which charts this reader may read, and build everything below
    # from that. A cell whose chart is missing from `charts` renders "Chart not
    # found", which is not a card state. Its docname would also reveal the
    # refused chart: in a standard workbook, a docname is a readable title.
    # `resolve_for_read` alone decides whether a dashboard with no readable
    # chart is Not Found. It exempts writers.
    charts = charts_on(items)
    readable = {chart.name for chart in charts}

    items = [item for item in items if item.get("type") != "chart" or item.get("chart") in readable]

    return {
        "name": doc.name,
        "route": doc.route,
        "title": doc.title,
        "items": [present_item(item, readable) for item in items],
        # Every chart the dashboard names, presented as `get_chart` presents
        # one. A cell's height comes from its chart's config (a Number card
        # grows with its readings). So the client cannot lay out the grid
        # before it has them, and fetching them per card would reflow the page
        # as each one arrived.
        "charts": [present_chart(chart) for chart in charts],
        "vertical_compact_layout": bool(doc.vertical_compact_layout),
        "can_write": writable,
        "can_copy": copyable,
        # "Edit" opens the Builder on this workbook, and "Duplicate" copies it.
        # It is the only Builder detail here, so only a reader who may use one
        # of them gets it
        "workbook": doc.workbook if writable or copyable else None,
    }


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
def get_chart(chart: str, dashboard: str | None = None):
    """A chart's rendering config. The query behind it stays on the server."""
    doc = frappe.get_doc(CHART, resolve_chart(chart, dashboard))

    return {**present_chart(doc), "can_write": can_write(doc)}


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
@answers_refusal(lambda: {"columns": [], "rows": [], "executed_at": frappe.utils.now()})
def get_chart_data(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    force: bool = False,
    page: int = 1,
):
    """A chart's rows, fetched under the permissions its Run as owner setting selects.

    `filters` is the dashboard filter state, keyed by filter name.
    `card_filters` is the reader's own filter on this card. It names a column
    the card shows, so it exposes nothing the card does not. Pages past the
    first are for readers `can_read_rows` allows. Everyone else gets the
    chart's one page.

    A chart that reads a table or a permlevel column the reader may not read is
    **Not Permitted**: it does not run, and the answer names the doctypes it
    needs.
    """
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return chart_answer(doc, routed_filters(name, dashboard, filters), card_filters, force, page)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
def get_chart_count(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    force: bool = False,
):
    """The total number of rows behind the pages of `get_chart_data`, under the same filters.

    For readers `can_read_rows` allows. A refusal raises, because the card asks
    for the count only when its data answer allowed it.
    """
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return doc.count_rows(routed_filters(name, dashboard, filters), card_filters, force=force)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
def download_chart_rows(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    format: str = "csv",
):
    """Every row behind the pages of `get_chart_data` as a file, under the same filters."""
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return doc.export_rows(format, routed_filters(name, dashboard, filters), card_filters)


def chart_answer(
    doc, adhoc_filters: dict | None, card_filters: list | None, force: bool = False, page: int = 1
) -> dict:
    """A saved chart's data, as its reader gets it.

    A chart with a missing required setting returns which one, as the Builder
    shows its author, and runs nothing.
    """
    if errors := config_errors(doc.chart_type, doc.query, frappe.parse_json(doc.config or "{}")):
        return {"errors": errors}

    # present the chart before fetching rows. If a query is saved during the
    # fetch, the card keeps the older `modified`, so a drill is refused instead
    # of running on the changed pipeline
    chart = present_chart(doc)
    result = doc.fetch(force=force, adhoc_filters=adhoc_filters, card_filters=card_filters, page=page)
    reads_rows = can_read_rows(doc)

    return {
        # the chart these rows came from. The card renders both together, so
        # its config always matches its rows
        "chart": chart,
        "columns": result["columns"],
        "rows": result["rows"],
        "granularity": result["granularity"],
        # a cell holds only a value, which cannot say it names a document. Every
        # chart is checked, and a chart that groups its rows gets none
        **({"record_links": result["record_links"]} if result.get("record_links") else {}),
        # the series for the sparkline of a Number card with a Period. Other
        # charts omit the key
        **({"sparkline": result["sparkline"]} if result.get("sparkline") else {}),
        **({"comparison_rows": result["comparison_rows"]} if result.get("comparison_rows") else {}),
        # which of the reader's permissions narrowed these rows, so the card
        # can say the number is not the total
        **result["scope"],
        # the drill menu opens on a click, so its options come with the card
        # instead of a request while the reader waits. `can_rows` comes with
        # them for the same reason: the menu shows "View rows", and the server
        # decides who may have them
        "drill": {
            "dimensions": drill_dimensions(doc) if reads_rows else [],
            "can_rows": reads_rows,
        },
        "can_filter": can_filter_card(doc.name),
        # whether the reader may page past the saved chart, count its rows and
        # download them. The card shows each control only when it will work;
        # the endpoints still decide
        "can_read_rows": reads_rows,
        "can_export": can_export(doc),
        # the symbol of every currency code in these rows. Codes arrive with
        # the rows, so this is the only source for the client's symbol map,
        # which starts with only the site's own currency
        "currency_symbols": result["currency_symbols"],
        # the date this card's Spans resolved against, so a drill uses the same
        # date as the number
        "read_on": result["read_on"],
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
    }


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
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
    """The data behind a segment of a chart, one drill level at a time.

    `drill_stack` is the reader's path, one level per click. Each level names
    the segment clicked as `segment_filters` (dimension values as (column,
    operator, literal) triples) and an `action`: `{"rows": true}` or
    `{"breakdown": column}`. An action may also name the `measure` clicked and,
    on a breakdown, the `granularity` to group by. Segments accumulate down the
    stack, and the last level's action decides the answer.

    The grain matters even when the reader did not choose it. A click on a
    date group of a breakdown sends only the group's start time. Only the level
    that made the group records its grain, so the client copies the
    `granularity` of each answer back onto its level.

    The request names only the chart. The server derives the chart's
    operations again, cuts them before the aggregation step, and refuses any
    column that is not on the surface under it. So the request cannot widen
    what a chart exposes.

    The answer says how to render it: `ordered`, whether the rows have an order
    of their own rather than a ranking, and `granularity`, the grain they were
    grouped by. So the client never infers either from a column type.

    The server reads a rows level as the reader asked, because the pipeline
    never leaves the server. `row_filters` are the reader's own filters on the
    rows, as (column, operator, value) triples on the surface. `sort` names
    surface columns and their directions, the first one primary. `find` is one
    term, matched across the surface's text and number columns. `page` is the
    page to return, at the page size `total_row_count` is counted for. All four
    apply to the same cut, so a filter narrows the total as well as the page. A
    breakdown level ignores them.

    A rows level also says whether this reader may download the cut, so the
    dialog shows the control only when it will work.

    A refusal is a normal answer here. `DrillLevelData` includes
    `not_permitted`, and `DrillDialog` renders it as a card renders a Not
    Permitted chart. So the level says the reader may not read the rows,
    instead of showing a Retry that cannot succeed.
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


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
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
    """The rows behind a segment as a file, with the reader's own filters, sort and find.

    The same cut that `get_drill_data` returns a page of, in full up to the
    download row limit. The request includes no more than that one does: the
    chart, the segments, and how to read them.
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


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
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
    """The values listed by the reader's own filter on a rows level.

    Checked and limited like the level itself. Only a column of the chart's
    surface is allowed, and the values come from the cut the reader is reading,
    not from the table under it.
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


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
@answers_refusal(lambda: None)
def get_drill_rows_range(
    chart: str,
    column: str,
    drill_stack: list | None = None,
    dashboard: str | None = None,
    filters: dict | None = None,
    row_filters: list | None = None,
):
    """The range shown by a number filter on a rows level, limited like its values."""
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
    """Refuse a guest the drill behind a chart they can see.

    A public chart shows only its saved data. Letting anonymous readers read
    the rows behind it must be a deliberate decision, not a side effect of the
    dashboard's visibility.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Sign in to see what is behind this chart"), exc=frappe.PermissionError)


def routed_filters(chart: str, dashboard: str | None, filters: dict | None) -> dict | None:
    """Dashboard filter state, routed to the queries behind one card.

    The filter links name queries and columns, which a View never receives. So
    a View sends filter state by filter name, and this side turns it into
    filters a query can run.

    A dashboard routes only the charts on it. A filter's links are not checked
    on save, so a filter on the caller's own dashboard could name any chart and
    any column of its query.
    """
    if not dashboard:
        return None

    resolve_chart(chart, dashboard)
    items = frappe.db.get_value(DASHBOARD, resolve_for_read(DASHBOARD, dashboard), "items")
    return route_filters(items, chart, filters)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
@answers_refusal(list)
def get_filter_values(
    dashboard: str,
    filter_name: str,
    search_term: str | None = None,
    filters: dict | None = None,
):
    """The values a filter on this dashboard lists.

    The View names the filter. The column behind it is looked up here, because
    the link that names it never leaves the server. The lookup runs under the
    permissions of the chart the filter is linked to, so it lists only values
    that user may see.

    `filters` is the current state of the other filters, keyed by filter name,
    the same shape `routed_filters` takes. It goes through `route_filters` too,
    without this filter itself. Narrowing a filter's values by its own current
    value would make picking a second value impossible.
    """
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))

    def values(chart, query, column):
        adhoc_filters = route_filters(doc.items, chart, filters, exclude_filter=filter_name)
        return query.distinct_column_values(column, search_term=search_term, adhoc_filters=adhoc_filters)

    return doc.lookup_filter(filter_name, values, missing=not_found)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
@answers_refusal(lambda: None)
def get_filter_range(dashboard: str, filter_name: str, filters: dict | None = None):
    """The range a filter on this dashboard shows.

    Looked up and routed like `get_filter_values`, because a picker's preset
    ranges and its list of values describe the same rows.
    """
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))

    def column_range(chart, query, column):
        adhoc_filters = route_filters(doc.items, chart, filters, exclude_filter=filter_name)
        return query.column_range(column, adhoc_filters=adhoc_filters)

    return doc.lookup_filter(filter_name, column_range, missing=not_found)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
@answers_refusal(list)
def get_card_values(chart: str, column: str, dashboard: str | None = None, search_term: str | None = None):
    """The values listed by the reader's own filter on one card.

    Only a column the card shows is allowed. A column with no source column (a
    measure, or a column a pivot made) lists nothing. The card's own filters
    narrow the list, so it lists only what the card shows.
    """
    source = card_source(chart, dashboard, column)
    if not source:
        return []
    doc, query, column_name, card_filters = source

    with runs_as(doc):
        return frappe.get_cached_doc(QUERY, query).distinct_column_values(
            column_name, search_term=search_term, adhoc_filters=card_filters
        )


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read lets a guest read Public content only
@answers_refusal(lambda: None)
def get_card_range(chart: str, column: str, dashboard: str | None = None):
    """The range shown by the reader's own filter on one card, narrowed like `get_card_values`."""
    source = card_source(chart, dashboard, column)
    if not source:
        return None
    doc, query, column_name, card_filters = source

    with runs_as(doc):
        return frappe.get_cached_doc(QUERY, query).column_range(column_name, adhoc_filters=card_filters)


def card_source(chart: str, dashboard: str | None, column: str):
    """The chart of a card filter, and the query and column the filter applies to.

    None when the column has no values to list. A column the card does not
    show is Not Found, like any other reference the caller may not read.
    """
    doc = frappe.get_doc(CHART, resolve_chart(chart, dashboard))
    query, column_name, card_filters = card_filter_source(doc.name, column)
    if not query:
        not_found()
    if not column_name:
        return None
    return doc, query, column_name, card_filters


def resolve_chart(chart: str, dashboard: str | None) -> str:
    """The chart a reference names, if the user may read it.

    A chart on a dashboard is read through the dashboard's visibility: the
    controller grants the dashboard's level to its charts, so the read check
    below is enough. The dashboard must resolve first, and the chart must be on
    it. Otherwise the answer is Not Found, as for any other reference the
    caller may not read.
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
    """One dashboard item, reduced to what a View renders.

    `readable` holds the charts this reader may read, decided in
    `get_dashboard`. A name outside it is refused content, and a docname
    reveals content as much as a title does.
    """
    presented = {
        "type": item.get("type"),
        "layout": item.get("layout"),
        # the author's layouts for narrower grids. Most items have none: the
        # client derives a missing breakpoint from the widest layout, because
        # only the client knows the width
        "layouts": item.get("layouts") or {},
    }

    if item.get("type") == "chart":
        presented["chart"] = item.get("chart")
        # the `id` of the Number chart reading this cell shows. A chart has
        # several readings and a cell shows one, so only the cell records which
        presented["reading"] = item.get("reading")
    elif item.get("type") == "text":
        presented["text"] = item.get("text")
    elif item.get("type") == "filter":
        # `links` stays on the server: it names the query and column a filter
        # applies to, and the server routes filters. Which cards a filter
        # changes is presentation: it decides what refetches and which empty
        # card can blame a filter. So only the chart names are sent.
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
    """Every chart on the dashboard that this reader may read, once each, in order.

    The controller grants the dashboard's level to its charts, but the level
    does not decide alone. A User Permission that limits the reader to one
    query refuses a chart on another. `resolve_chart` asks `may_read` for the
    same chart moments later. Asking it here too keeps a chart's title and
    config from reaching a reader whose card would then be refused.

    A cell whose chart was deleted is left out too. That is a stale layout, not
    a refused read.
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
    """A chart, reduced to what its card needs. The query behind it stays here."""
    return {
        "name": doc.name,
        "title": doc.title,
        "chart_type": doc.chart_type,
        "config": present_config(doc.config),
        # a drill sends it back, and is refused once the chart or a query it
        # reads has changed
        "modified": doc.last_modified(),
    }


def present_config(config) -> dict:
    """The chart config without its filters, which describe the data and not the rendering."""
    config = frappe.parse_json(config or "{}")
    config.pop("filters", None)
    return config
