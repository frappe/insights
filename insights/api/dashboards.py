import frappe
from frappe.query_builder.functions import Count

from insights.api.list_filters import (
    get_content_filters,
    get_last_opened,
    get_source_filters,
    match_records,
)
from insights.decorators import insights_whitelist
from insights.insights.query_utils import source_tables
from insights.permissions import can_write

DASHBOARD = "Insights Dashboard v3"
DASHBOARD_CHART = "Insights Dashboard Chart v3"


def _match_charts(is_pattern: bool, values: list) -> list:
    """Dashboards showing a picked chart, or a chart whose title matches."""
    charts = match_records("Insights Chart v3", "name")(is_pattern, values)
    if not charts:
        return []
    return frappe.get_all(
        DASHBOARD_CHART,
        filters={"parenttype": DASHBOARD, "chart": ["in", charts]},
        pluck="parent",
        distinct=True,
    )


def _match_data_sources(is_pattern: bool, values: list) -> list | None:
    """Dashboards that show a chart built on one of the picked data sources.

    Only charts the caller may read count. Only exact names match, not patterns.
    A chart's reader may learn which data source it reads, but a pattern would
    probe the text of a query they may not read. `is set` arrives as the
    pattern `%`, which matches every name.
    """
    if is_pattern and values != ["%"]:
        return None

    # Start from the dashboards the caller can list. Only their charts can
    # match, and listing every readable chart takes seconds on a large site.
    shown = frappe.get_all(
        DASHBOARD_CHART,
        filters={
            "parenttype": DASHBOARD,
            "parent": ["in", frappe.get_list(DASHBOARD, pluck="name", limit=0)],
        },
        pluck="chart",
        distinct=True,
    )
    if not shown:
        return []

    picked = set(values)
    sources_of = {}
    charts = []
    readable = frappe.get_list(
        "Insights Chart v3", filters={"name": ["in", shown]}, fields=["name", "query"], limit=0
    )
    for chart in readable:
        if not chart.query:
            continue
        if chart.query not in sources_of:
            sources_of[chart.query] = {table["data_source"] for table in source_tables(chart.query)}
        sources = sources_of[chart.query]
        if sources and (is_pattern or sources & picked):
            charts.append(chart.name)
    return _match_charts(False, charts) if charts else []


def _get_favourites() -> list:
    return frappe.get_all(
        DASHBOARD, filters={"_liked_by": ["like", f'%"{frappe.session.user}"%']}, pluck="name"
    )


# Filters the list's filter control declares beyond the dashboard's own columns
DASHBOARD_FILTERS = {
    "name": match_records(DASHBOARD, "name"),
    "chart": _match_charts,
    "data_source": _match_data_sources,
}


@insights_whitelist()
def get_dashboards(
    limit: int = 50,
    sources: list | None = None,
    filters: list | None = None,
):
    """Return dashboards from the chosen sources: favourites, then the rest.

    Each part is ordered by the user's last open, then by last modified.
    Favourites always come back whole; `limit` counts the rest. `sources` is as
    for `get_workbooks`.
    """
    list_filters = get_content_filters(filters or [], DASHBOARD_FILTERS)
    list_filters += get_source_filters(DASHBOARD, sources)

    opened = get_last_opened(DASHBOARD)
    favourites = _get_favourites()
    dashboards = _opened_first([*list_filters, ["name", "in", favourites]], opened, 0) if favourites else []
    rest = [*list_filters, ["name", "not in", favourites]] if favourites else list_filters
    dashboards += _opened_first(rest, opened, limit)

    _enrich_dashboards(dashboards)
    return dashboards


def _opened_first(filters: list, opened: dict, limit: int) -> list:
    """Dashboards the user opened, last opened first, then the rest by last modified."""
    dashboards = []
    if opened:
        dashboards = frappe.get_list(
            DASHBOARD,
            filters=[*filters, ["name", "in", list(opened)]],
            fields=DASHBOARD_LIST_FIELDS,
            limit=0,
        )
        dashboards.sort(key=lambda d: opened[str(d.name)], reverse=True)
        dashboards = dashboards[:limit] if limit else dashboards
    if not limit or len(dashboards) < limit:
        dashboards += frappe.get_list(
            DASHBOARD,
            filters=[*filters, ["name", "not in", list(opened)]] if opened else filters,
            fields=DASHBOARD_LIST_FIELDS,
            order_by="modified desc",
            limit=limit - len(dashboards) if limit else 0,
        )
    return dashboards


DASHBOARD_LIST_FIELDS = [
    "name",
    "title",
    "owner",
    "workbook",
    "creation",
    "modified",
    "preview_image",
    "_liked_by",
]


def _enrich_dashboards(dashboards):
    view_counts = dashboard_view_counts([dashboard.name for dashboard in dashboards])
    user = frappe.session.user
    for dashboard in dashboards:
        dashboard["views"] = view_counts.get(str(dashboard.name), 0)
        dashboard["is_favourite"] = bool(dashboard._liked_by) and user in frappe.as_json(dashboard._liked_by)
        # the list shows the preview refresh only to editors
        dashboard["can_write"] = can_write(frappe.get_doc(DASHBOARD, dashboard.name))


def dashboard_view_counts(names: list[str], since: str | None = None) -> dict[str, int]:
    """Opens per dashboard, over every open or only those after `since`."""
    if not names:
        return {}
    view_log = frappe.qb.DocType("View Log")
    query = (
        frappe.qb.from_(view_log)
        .select(view_log.reference_name, Count(view_log.name).as_("views"))
        .where(
            (view_log.reference_doctype == "Insights Dashboard v3")
            # reference_name is stored as a string; cast names to match
            & view_log.reference_name.isin([str(name) for name in names])
        )
        .groupby(view_log.reference_name)
    )
    if since:
        query = query.where(view_log.creation >= since)
    rows = query.run(as_dict=True)
    return {str(row.reference_name): row.views for row in rows}


@insights_whitelist()
def update_dashboard_preview(dashboard_name: str):
    """Regenerate the preview image from the caller's rows.

    Every reader of the dashboard list sees this image, so only an editor may
    regenerate it. A save regenerates it too.
    """
    frappe.has_permission(DASHBOARD, ptype="read", doc=dashboard_name, throw=True)
    dashboard = frappe.get_doc(DASHBOARD, dashboard_name)
    if not can_write(dashboard):
        frappe.throw(
            frappe._("Only an editor of this dashboard can refresh its preview"), frappe.PermissionError
        )
    return dashboard.generate_dashboard_preview()
