import frappe
from frappe.query_builder.functions import Count, Max

from insights.api.permissions import is_private
from insights.decorators import insights_whitelist, validate_type


@insights_whitelist()
def get_dashboard_list():
    dashboards = frappe.get_list(
        "Insights Dashboard",
        fields=["name", "title", "modified", "_liked_by"],
    )
    for dashboard in dashboards:
        if dashboard._liked_by:
            dashboard["is_favourite"] = frappe.session.user in frappe.as_json(dashboard._liked_by)
        dashboard["charts"] = frappe.get_all(
            "Insights Dashboard Item",
            filters={
                "parent": dashboard.name,
                "item_type": ["not in", ["Text", "Filter"]],
            },
            pluck="parent",
        )
        dashboard["charts_count"] = len(dashboard["charts"])
        dashboard["view_count"] = frappe.db.count(
            "View Log",
            filters={
                "reference_doctype": "Insights Dashboard",
                "reference_name": dashboard.name,
            },
        )

        dashboard["is_private"] = is_private("Insights Dashboard", dashboard.name)

    return dashboards


@insights_whitelist()
def create_dashboard(title: str):
    dashboard = frappe.get_doc({"doctype": "Insights Dashboard", "title": title})
    dashboard.insert()
    return {
        "name": dashboard.name,
        "title": dashboard.title,
    }


@insights_whitelist()
def get_dashboard_options(chart: str):
    # find all dashboards that don't have the chart within the allowed dashboards
    Dashboard = frappe.qb.DocType("Insights Dashboard")
    DashboardItem = frappe.qb.DocType("Insights Dashboard Item")

    return (
        frappe.qb.from_(Dashboard)
        .left_join(DashboardItem)
        .on(Dashboard.name == DashboardItem.parent)
        .select(Dashboard.name.as_("value"), Dashboard.title.as_("label"))
        .where(DashboardItem.chart != chart)
        .groupby(Dashboard.name)
        .run(as_dict=True)
    )


@insights_whitelist()
def add_chart_to_dashboard(dashboard: str, chart: str):
    dashboard = frappe.get_doc("Insights Dashboard", dashboard)
    dashboard.add_chart(chart)
    dashboard.save()


# v3 API


@insights_whitelist()
def get_dashboards(
    search_term: str | None = None,
    limit: int = 50,
    get_favorites: bool = False,
    folder: str | None = None,
    scope: str | None = None,
):
    """Return dashboards, optionally limited to a workbook folder.

    Dashboards inherit categorization from their workbook (no folder field of
    their own), so `folder` filters to dashboards whose workbook is filed there.
    Use the sentinel "" / "root" to restrict to dashboards of unfiled workbooks.

    scope (a personal lens, spans folders):
        "owned"  -> only dashboards created by the current user
        "shared" -> only dashboards created by someone else (still permission filtered)
    """
    filters = {}
    if get_favorites:
        filters["_liked_by"] = ["like", f"%{frappe.session.user}%"]

    if scope == "owned":
        filters["owner"] = frappe.session.user
    elif scope == "shared":
        filters["owner"] = ["!=", frappe.session.user]

    if folder is not None:
        folder_workbooks = frappe.get_all(
            "Insights Workbook",
            filters={"folder": ["is", "not set"]} if folder in ("", "root") else {"folder": folder},
            pluck="name",
        )
        # workbook link is stored as a string; cast to match
        filters["workbook"] = ["in", [str(name) for name in folder_workbooks] or [""]]

    dashboards = frappe.get_list(
        "Insights Dashboard v3",
        or_filters={
            "name": ["like", f"%{search_term}%" if search_term else "%"],
            "title": ["like", f"%{search_term}%" if search_term else "%"],
        },
        filters=filters,
        fields=DASHBOARD_LIST_FIELDS,
        order_by="creation desc",
        limit=limit,
    )

    _enrich_dashboards(dashboards)
    return dashboards


@insights_whitelist()
def get_recent_dashboards(search_term: str | None = None, limit: int = 20):
    """Dashboards the current user viewed most recently, newest first.

    Recency comes from the per-user View Log (populated by `track_view` on
    every dashboard open), so it spans folders and reflects opens from
    anywhere, not just this list.
    """
    view_log = frappe.qb.DocType("View Log")
    recent = (
        frappe.qb.from_(view_log)
        .select(view_log.reference_name, Max(view_log.modified).as_("last_viewed"))
        .where(
            (view_log.viewed_by == frappe.session.user)
            & (view_log.reference_doctype == "Insights Dashboard v3")
        )
        .groupby(view_log.reference_name)
        .orderby(Max(view_log.modified), order=frappe.qb.desc)
        .limit(limit)
        .run(as_dict=True)
    )
    order = {row.reference_name: i for i, row in enumerate(recent)}
    if not order:
        return []

    dashboards = frappe.get_list(
        "Insights Dashboard v3",
        or_filters={
            "name": ["like", f"%{search_term}%" if search_term else "%"],
            "title": ["like", f"%{search_term}%" if search_term else "%"],
        },
        filters={"name": ["in", list(order.keys())]},
        fields=DASHBOARD_LIST_FIELDS,
        limit=0,
    )

    _enrich_dashboards(dashboards)
    # get_list ignores the View Log order and silently drops dashboards the user
    # can no longer access, so re-sort by recency over what survived
    dashboards.sort(key=lambda dashboard: order[dashboard.name])
    return dashboards


DASHBOARD_LIST_FIELDS = [
    "name",
    "title",
    "workbook",
    "creation",
    "modified",
    "preview_image",
    "_liked_by",
]


def _enrich_dashboards(dashboards):
    # batch counts into one grouped query each instead of per-dashboard queries
    # (avoids N+1s over the whole list)
    names = [dashboard.name for dashboard in dashboards]
    view_counts = _dashboard_view_counts(names)
    chart_counts = _dashboard_chart_counts(names)
    user = frappe.session.user
    for dashboard in dashboards:
        dashboard["charts"] = chart_counts.get(str(dashboard.name), 0)
        dashboard["views"] = view_counts.get(str(dashboard.name), 0)
        if dashboard._liked_by:
            dashboard["is_favourite"] = user in frappe.as_json(dashboard._liked_by)


def _dashboard_view_counts(names: list[str]) -> dict[str, int]:
    if not names:
        return {}
    view_log = frappe.qb.DocType("View Log")
    rows = (
        frappe.qb.from_(view_log)
        .select(view_log.reference_name, Count(view_log.name).as_("views"))
        .where(
            (view_log.reference_doctype == "Insights Dashboard v3")
            # reference_name is stored as a string; cast names to match
            & view_log.reference_name.isin([str(name) for name in names])
        )
        .groupby(view_log.reference_name)
        .run(as_dict=True)
    )
    return {str(row.reference_name): row.views for row in rows}


def _dashboard_chart_counts(names: list[str]) -> dict[str, int]:
    # one chart == one row in the `linked_charts` child table (rebuilt from
    # `items` on every save), so count rows per parent instead of parsing items
    if not names:
        return {}
    linked_chart = frappe.qb.DocType("Insights Dashboard Chart v3")
    rows = (
        frappe.qb.from_(linked_chart)
        .select(linked_chart.parent, Count(linked_chart.name).as_("charts"))
        .where(
            (linked_chart.parenttype == "Insights Dashboard v3")
            & linked_chart.parent.isin([str(name) for name in names])
        )
        .groupby(linked_chart.parent)
        .run(as_dict=True)
    )
    return {str(row.parent): row.charts for row in rows}


@insights_whitelist()
@validate_type
def update_dashboard_preview(dashboard_name: str):
    dashboard = frappe.get_doc("Insights Dashboard v3", dashboard_name)
    file_url = dashboard.generate_dashboard_preview()
    return file_url
