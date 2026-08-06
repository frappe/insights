# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What a viewer surface is allowed to ask for.

The islands mount on a desk page for a user who may hold no Insights role at
all, so these endpoints are plain `frappe.whitelist(allow_guest=True)`: who may
see what is decided by the permission controller through the visibility ladder,
never by a role check here. A guest reaches only the `Public` rung, and reaches
it through the same code path as everyone else.

Every reference goes through `resolve_for_read`, which answers a missing
reference and a denied one identically. Nothing below re-checks the read after
it, and nothing catches its error — either would give the answer away.

Rendering is all these responses carry. Operations, SQL and the query documents
behind a chart never cross this boundary: the client says which chart, the
server decides what runs.
"""

import re

import frappe
from frappe import _

from insights.decorators import validate_type
from insights.insights.doctype.insights_data_source_v3.data_authority import data_authority_of
from insights.permissions import check_app_permission
from insights.resolver import CHART, DASHBOARD, ContentNotAvailableError, resolve, resolve_for_read

QUERY = "Insights Query v3"

# a filter item links a chart as "links": { '<chart>': "`<query>`.`<column>`" }
FILTER_LINK_PATTERN = r"^`([^`]+)`\.`([^`]+)`$"


@frappe.whitelist(allow_guest=True)
@validate_type
def get_dashboard(dashboard: str):
    """A dashboard as a viewer surface needs it: what to lay out, and what it may offer."""
    doc = frappe.get_doc(DASHBOARD, resolve_for_read(DASHBOARD, dashboard))
    editable = can_edit(doc)

    return {
        "name": doc.name,
        "slug": doc.slug,
        "title": doc.title,
        "items": [present_item(item) for item in frappe.parse_json(doc.items) or []],
        "vertical_compact_layout": bool(doc.vertical_compact_layout),
        "modified": doc.modified,
        "can_edit": editable,
        # where "Edit in Insights" lands: the builder is workbook-scoped. It is the
        # one piece of authoring structure here, so only an editor is told it
        "workbook": doc.workbook if editable else None,
        # standard content is read-only on a site, so duplicating is the only way
        # to change it — and changing it means an authoring seat
        "can_duplicate": bool(doc.is_standard) and check_app_permission(),
    }


@frappe.whitelist(allow_guest=True)
@validate_type
def get_chart(chart: str, dashboard: str | None = None):
    """A chart's rendering config. The query it draws from stays server-side."""
    doc = frappe.get_doc(CHART, resolve_chart(chart, dashboard))

    return {
        "name": doc.name,
        "title": doc.title,
        "chart_type": doc.chart_type,
        "config": present_config(doc.config),
        "can_edit": can_edit(doc),
    }


@frappe.whitelist(allow_guest=True)
@validate_type
def get_chart_data(
    chart: str,
    dashboard: str | None = None,
    filters: dict | None = None,
    force: bool = False,
):
    """A chart's rows, fetched under the authority the chart declares.

    `filters` is dashboard filter state, keyed by filter name. Routing it to the
    queries behind the charts is this side's job — the links that do the routing
    name queries and columns, which is exactly what a viewer never receives.
    """
    name = resolve_chart(chart, dashboard)
    doc = frappe.get_doc(CHART, name)

    adhoc_filters = None
    if dashboard:
        adhoc_filters = adhoc_filters_for(resolve_for_read(DASHBOARD, dashboard), name, filters)

    result = doc.get_data(
        force=force,
        page_size=frappe.parse_json(doc.config or "{}").get("limit") or 100,
        adhoc_filters=adhoc_filters,
    )

    return {
        "columns": result["columns"],
        "rows": result["rows"],
        "granularity": column_granularity(doc),
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
    }


@frappe.whitelist(allow_guest=True)
@validate_type
def get_filter_values(dashboard: str, filter_name: str, search_term: str | None = None):
    """The values a filter on this dashboard offers.

    A viewer names the filter; the column behind it is looked up here, because the
    link that names it is exactly what never crosses the boundary. The lookup runs
    under the authority of the chart the filter is linked to, so the values on
    offer are the ones that user is allowed to see.
    """
    dashboard_name = resolve_for_read(DASHBOARD, dashboard)
    chart, query, column = filter_source(dashboard_name, filter_name)

    query_doc = frappe.get_cached_doc(QUERY, query)
    # the whitelisted method carries an `Insights User` role check, which is the
    # SPA's boundary and not this one: a viewer surface holds no role by
    # definition, and the read was already settled above. The undecorated method
    # is the same computation without that gate. The doctype should split the
    # check off the method instead — see ticket 18.
    distinct_column_values = query_doc.get_distinct_column_values.__wrapped__

    with data_authority_of(frappe.get_doc(CHART, chart)):
        return distinct_column_values(query_doc, column, search_term=search_term)


def filter_source(dashboard: str, filter_name: str) -> tuple[str, str, str]:
    """The chart, query and column a named dashboard filter reads its values from."""
    items = frappe.parse_json(frappe.db.get_value(DASHBOARD, dashboard, "items") or "[]")

    for item in items:
        if item.get("type") != "filter" or item.get("filter_name") != filter_name:
            continue

        for chart, link in (item.get("links") or {}).items():
            match = re.match(FILTER_LINK_PATTERN, link) if link else None
            if match and is_on_dashboard(chart, dashboard):
                return chart, *match.groups()

    not_available()


def resolve_chart(chart: str, dashboard: str | None) -> str:
    """The chart a reference names, for a user who may read it.

    A chart reached through a dashboard is carried by the dashboard's audience:
    the controller already cascades a dashboard's rung to the charts on it, so
    the read check below is the whole check. The dashboard must resolve first
    and the chart must really be on it, or the reference answers like any other
    reference the caller may not have.
    """
    if not dashboard:
        return resolve_for_read(CHART, chart)

    dashboard_name = resolve_for_read(DASHBOARD, dashboard)
    name = resolve(CHART, chart)
    if not name or not is_on_dashboard(name, dashboard_name):
        not_available()

    return resolve_for_read(CHART, name)


def not_available():
    """The one answer for anything the caller may not have.

    Same type and same message as the resolver's, so a chart that is not on the
    dashboard reads exactly like a chart that does not exist.
    """
    frappe.throw(_("This content is not available"), exc=ContentNotAvailableError)


def is_on_dashboard(chart: str, dashboard: str) -> bool:
    items = frappe.parse_json(frappe.db.get_value(DASHBOARD, dashboard, "items") or "[]")
    return any(item.get("type") == "chart" and item.get("chart") == chart for item in items)


def can_edit(doc) -> bool:
    """Everything editing takes: rights on the document, and a seat in the app.

    Shipped content answers no even to its owner — it is read-only on a site
    outside developer mode (`insights.bundles.block_standard_edits`), and
    `can_duplicate` is the affordance that replaces it.
    """
    if doc.is_standard and not frappe.conf.developer_mode:
        return False

    return bool(frappe.has_permission(doc.doctype, ptype="write", doc=doc.name)) and check_app_permission()


def present_item(item: dict) -> dict:
    """One dashboard item, reduced to what a viewer renders it from."""
    presented = {"type": item.get("type"), "layout": item.get("layout")}

    if item.get("type") == "chart":
        presented["chart"] = item.get("chart")
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


def present_config(config) -> dict:
    """The chart config, minus the parts that describe the data instead of the picture."""
    config = frappe.parse_json(config or "{}")
    config.pop("filters", None)
    return config


def column_granularity(chart) -> dict:
    """The grain each date column was grouped by, so the client can format it.

    The grain lives in the query's summarize or pivot step. The step itself
    never crosses the wire — only the grain, per column.
    """
    operations = frappe.parse_json(frappe.db.get_value(QUERY, chart.get_data_query(), "operations") or "[]")

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


def adhoc_filters_for(dashboard: str, chart: str, filter_states: dict | None) -> dict | None:
    """Dashboard filter state, routed to the queries the filters are linked to."""
    if not filter_states:
        return None

    items = frappe.parse_json(frappe.db.get_value(DASHBOARD, dashboard, "items") or "[]")
    filters_by_query = {}

    for item in items:
        if item.get("type") != "filter":
            continue

        state = filter_states.get(item.get("filter_name")) or {}
        if not state.get("operator"):
            continue

        link = (item.get("links") or {}).get(chart)
        match = re.match(FILTER_LINK_PATTERN, link) if link else None
        if not match:
            continue

        query, column = match.groups()
        group = filters_by_query.setdefault(
            query, {"type": "filter_group", "logical_operator": "And", "filters": []}
        )
        group["filters"].append(
            {
                "type": "filter",
                "column": {"type": "column", "column_name": column},
                "operator": state["operator"],
                "value": state.get("value"),
            }
        )

    return filters_by_query or None
