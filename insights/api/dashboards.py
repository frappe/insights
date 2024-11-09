import frappe

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
            dashboard["is_favourite"] = frappe.session.user in frappe.as_json(
                dashboard._liked_by
            )
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
def create_dashboard(title):
    dashboard = frappe.get_doc({"doctype": "Insights Dashboard", "title": title})
    dashboard.insert()
    return {
        "name": dashboard.name,
        "title": dashboard.title,
    }


@insights_whitelist()
def get_dashboard_options(chart):
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
def add_chart_to_dashboard(dashboard, chart):
    dashboard = frappe.get_doc("Insights Dashboard", dashboard)
    dashboard.add_chart(chart)
    dashboard.save()


# v3 API


@insights_whitelist()
def get_dashboards(search_term=None, limit=50):
    workbooks = frappe.get_list(
        "Insights Workbook",
        filters={"dashboards": ["like", f"%{search_term}%" if search_term else "%"]},
        fields=["name", "title", "dashboards", "modified"],
    )

    dashboards = []
    for workbook in workbooks:
        _dashboards = frappe.parse_json(workbook.dashboards)
        for dashboard in _dashboards:
            if len(dashboards) >= limit:
                break
            dashboards.append(
                {
                    "name": dashboard["name"],
                    "title": dashboard["title"],
                    "workbook": workbook.name,
                    "charts": len(dashboard["items"]),
                    "modified": workbook["modified"],
                    "preview_image": dashboard.get("preview_image"),
                }
            )

    return dashboards


def _get_workbook_name(dashboard_name: str):
    workbooks = frappe.get_all(
        "Insights Workbook",
        filters={"dashboards": ["like", f"%{dashboard_name}%"]},
        pluck="name",
    )

    if not workbooks:
        frappe.throw("Could not find workbook for dashboard")

    return workbooks[0]


@insights_whitelist()
def get_workbook_name(dashboard_name: str):
    return _get_workbook_name(dashboard_name)


@frappe.whitelist(allow_guest=True)
def fetch_workbook_dashboard(dashboard_name: str):
    workbook_name = _get_workbook_name(dashboard_name)
    workbook = frappe.get_doc("Insights Workbook", workbook_name)
    dashboards = frappe.parse_json(workbook.dashboards)
    return next((d for d in dashboards if d["name"] == dashboard_name), None)


@insights_whitelist()
@validate_type
def update_dashboard_preview(dashboard_name: str):
    workbook_name = _get_workbook_name(dashboard_name)
    workbook = frappe.get_doc("Insights Workbook", workbook_name)
    dashboard = next(
        (
            d
            for d in frappe.parse_json(workbook.dashboards)
            if d["name"] == dashboard_name
        ),
        None,
    )
    if not dashboard:
        frappe.throw("Could not find dashboard")

    file_url = workbook.update_dashboard_preview(dashboard["name"])
    workbook.save()
    return file_url
