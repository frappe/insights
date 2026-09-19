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

from insights.insights.doctype.insights_chart_v3.chart_drill import drill_data, drill_dimensions
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
    card_filter_source,
    route_filters,
)
from insights.permission_user import permission_user, permission_user_for
from insights.permissions import check_app_permission
from insights.resolver import CHART, DASHBOARD, resolve, resolve_for_read

QUERY = "Insights Query v3"


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_dashboard(dashboard: str, surface: str | None = None):
    """A dashboard as a view of it needs: what to lay out, and what it may offer.

    `surface` says which page the view is on, for the `dashboard_viewed` event.
    """
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))
    count_view(doc, surface)
    writable = can_write(doc)
    items = frappe.parse_json(doc.items) or []

    return {
        "name": doc.name,
        "route": doc.route,
        "title": doc.title,
        "items": [present_item(item) for item in items],
        # Every chart the grid names, presented as `get_chart` presents one. A
        # cell's height is derived from the config of the chart it draws — a
        # Number card is as tall as its readings make it — so a surface cannot
        # lay the grid out before it holds them, and fetching them per card
        # would reflow the page as each one landed.
        "charts": [present_chart(chart) for chart in charts_on(items)],
        "vertical_compact_layout": bool(doc.vertical_compact_layout),
        "modified": doc.modified,
        "can_write": writable,
        # where "Edit in Insights" lands: the builder is workbook-scoped. It is the
        # one piece of authoring structure here, so only an editor is told it
        "workbook": doc.workbook if writable else None,
        # standard content is read-only on a site, so copying is the only way to
        # change it — and changing it means an Insights role
        "can_copy": bool(doc.is_standard) and check_app_permission(),
    }


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_chart(chart: str, dashboard: str | None = None):
    """A chart's rendering config. The query it draws from stays server-side."""
    doc = frappe.get_doc(CHART, resolve_chart(chart, dashboard))

    return {**present_chart(doc), "can_write": can_write(doc)}


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_chart_data(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    force: bool = False,
):
    """A chart's rows, fetched under the permissions the chart declares.

    `filters` is dashboard filter state, keyed by filter name. `card_filters` is
    the reader's own filter on this card: it names a column the card draws, so
    it reaches no further than the picture already does.
    """
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    result = doc.get_data(
        force=force,
        adhoc_filters=routed_filters(name, dashboard, filters),
        card_filters=card_filters,
    )

    return {
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
        # the drill menu opens on a click, so what it can offer travels with the
        # card instead of costing a round trip at the moment latency is felt
        "drill": {"dimensions": drill_dimensions(doc) if can_drill() else []},
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
    }


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_drill_data(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    drill_stack: list | None = None,
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
    """
    if not can_drill():
        frappe.throw(_("Sign in to see what is behind this chart"), exc=frappe.PermissionError)

    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    return drill_data(doc, drill_stack, adhoc_filters=routed_filters(name, dashboard, filters))


def can_drill() -> bool:
    """Whether this session may look behind a chart it can see.

    A guest may not: a public chart stays a picture, and letting anonymous
    readers walk the rows behind it is a decision to make loudly, not one to
    inherit from the level the dashboard sits at.
    """
    return frappe.session.user != "Guest"


def routed_filters(chart: str, dashboard: str | None, filters: dict | None) -> dict | None:
    """Dashboard filter state, routed to the queries behind one card.

    The links that do the routing name queries and columns, which is exactly
    what a view never receives — so a view sends filter state by name and this
    side turns it into something a query can run.
    """
    if not dashboard:
        return None

    items = frappe.db.get_value(DASHBOARD, resolve_for_read(DASHBOARD, dashboard), "items")
    return route_filters(items, chart, filters)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
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
    source = doc.filter_source(filter_name)
    if not source:
        not_found()
    chart, query, column = source

    adhoc_filters = route_filters(doc.items, chart, filters, exclude_filter=filter_name)

    query_doc = frappe.get_cached_doc(QUERY, query)

    with permission_user(permission_user_for(frappe.get_doc(CHART, chart))):
        return query_doc.distinct_column_values(column, search_term=search_term, adhoc_filters=adhoc_filters)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_filter_range(dashboard: str, filter_name: str, filters: dict | None = None):
    """The range a filter on this dashboard offers.

    Looked up and routed the way `get_filter_values` is: the preset ranges a
    picker offers and the values it lists answer the same question about the
    same rows.
    """
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))
    source = doc.filter_source(filter_name)
    if not source:
        not_found()
    chart, query, column = source

    adhoc_filters = route_filters(doc.items, chart, filters, exclude_filter=filter_name)

    query_doc = frappe.get_cached_doc(QUERY, query)

    with permission_user(permission_user_for(frappe.get_doc(CHART, chart))):
        return query_doc.column_range(column, adhoc_filters=adhoc_filters)


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
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

    with permission_user(permission_user_for(doc)):
        return frappe.get_cached_doc(QUERY, query).distinct_column_values(
            column_name, search_term=search_term, adhoc_filters=card_filters
        )


@frappe.whitelist(allow_guest=True)  # nosemgrep - resolve_for_read admits a guest to Public content only
def get_card_range(chart: str, column: str, dashboard: str | None = None):
    """The range a reader's own filter on one card offers, narrowed as `get_card_values` is."""
    source = card_source(chart, dashboard, column)
    if not source:
        return None
    doc, query, column_name, card_filters = source

    with permission_user(permission_user_for(doc)):
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


def not_found():
    """The one answer for anything the caller may not have.

    Same type and same message as the resolver's, so a chart that is not on the
    dashboard reads exactly like a chart that does not exist.
    """
    frappe.throw(_("Not Found"), exc=frappe.DoesNotExistError)


def is_on_dashboard(chart: str, dashboard: str) -> bool:
    items = frappe.parse_json(frappe.db.get_value(DASHBOARD, dashboard, "items") or "[]")
    return any(item.get("type") == "chart" and item.get("chart") == chart for item in items)


def count_view(doc, surface: str | None = None):
    """Record that this reader opened this dashboard, for their own "Recents".

    Opening a dashboard is the same act on every surface, so it counts on every
    surface: the desk island, the public link and the app's own page all reach a
    dashboard through here, and a reader looking for what they read last does
    not care which page they read it on. The dashboard keeps the counting — it
    already drops repeats within five minutes.
    """
    doc.track_view(surface)


def can_write(doc) -> bool:
    """Everything editing takes: rights on the document, and an Insights role.

    Shipped content answers no even to its owner — it is read-only on a site
    outside developer mode, and `can_copy` is the affordance that replaces it.
    """
    if doc.is_standard and not frappe.conf.developer_mode:
        return False

    return bool(frappe.has_permission(doc.doctype, ptype="write", doc=doc.name)) and check_app_permission()


def present_item(item: dict) -> dict:
    """One dashboard item, reduced to what a view renders it from."""
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
                "charts": [chart for chart, link in (item.get("links") or {}).items() if link],
            }
        )

    return presented


def charts_on(items: list[dict]):
    """Every chart the grid names, once each, in the order the cells name them.

    A chart is read through the dashboard's visibility, which is the rule
    `resolve_chart` above already stands on: the controller grants a dashboard's
    level to the charts linked to it, so a reader who resolved the dashboard may
    read them all. A cell naming a chart that has since been deleted is skipped
    — the layout is wrong, not the read.
    """
    named = dict.fromkeys(item.get("chart") for item in items if item.get("type") == "chart")
    for name in named:
        if name and frappe.db.exists(CHART, name):
            yield frappe.get_cached_doc(CHART, name)


def present_chart(doc) -> dict:
    """A chart, reduced to what draws its card. The query behind it stays here."""
    return {
        "name": doc.name,
        "title": doc.title,
        "chart_type": doc.chart_type,
        "config": present_config(doc.config),
    }


def present_config(config) -> dict:
    """The chart config, minus the parts that describe the data instead of the picture."""
    config = frappe.parse_json(config or "{}")
    config.pop("filters", None)
    return config
