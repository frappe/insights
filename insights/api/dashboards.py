import frappe
from frappe.query_builder.functions import Count

from insights.api.list_filters import (
    get_content_filters,
    get_last_opened,
    get_source_filters,
    match_operations,
    match_records,
)
from insights.decorators import insights_whitelist

DASHBOARD = "Insights Dashboard v3"
DASHBOARD_CHART = "Insights Dashboard Chart v3"


def _match_charts(is_pattern: bool, values: list) -> list:
    """Dashboards showing a picked chart, or a chart whose title matches."""
    Link = frappe.qb.DocType(DASHBOARD_CHART)
    Chart = frappe.qb.DocType("Insights Chart v3")
    query = frappe.qb.from_(Link).select(Link.parent).where(Link.parenttype == DASHBOARD).distinct()
    if is_pattern:
        condition = Chart.title.like(values[0])
        for v in values[1:]:
            condition |= Chart.title.like(v)
        return query.join(Chart).on(Chart.name == Link.chart).where(condition).run(pluck=True)
    return query.where(Link.chart.isin(values)).run(pluck=True)


def _match_data_sources(is_pattern: bool, values: list) -> list:
    """Dashboards showing a chart whose query reads a matching data source."""
    queries = match_operations("data_source", "name")(is_pattern, values)
    if not queries:
        return []
    charts = frappe.get_all("Insights Chart v3", filters={"query": ["in", queries]}, pluck="name")
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
    frappe.has_permission("Insights Dashboard v3", ptype="read", doc=dashboard_name, throw=True)
    dashboard = frappe.get_doc("Insights Dashboard v3", dashboard_name)
    file_url = dashboard.generate_dashboard_preview()
    return file_url
