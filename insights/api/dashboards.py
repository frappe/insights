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
    dashboards = frappe.get_list(
        "Insights Dashboard v3",
        or_filters={
            "name": ["like", f"%{search_term}%" if search_term else "%"],
            "title": ["like", f"%{search_term}%" if search_term else "%"],
        },
        fields=[
            "name",
            "title",
            "workbook",
            "creation",
            "modified",
            "preview_image",
            "items",
        ],
        order_by="creation desc",
        limit=limit,
    )

    for dashboard in dashboards:
        items = frappe.parse_json(dashboard["items"])
        charts = [item for item in items if item["type"] == "chart"]
        dashboard["charts"] = len(charts)
        dashboard["views"] = frappe.db.count(
            "View Log",
            filters={
                "reference_doctype": "Insights Dashboard v3",
                "reference_name": dashboard.name,
            },
        )
        del dashboard["items"]

    return dashboards


@insights_whitelist()
@validate_type
def update_dashboard_preview(dashboard_name: str):
    dashboard = frappe.get_doc("Insights Dashboard v3", dashboard_name)
    file_url = dashboard.generate_dashboard_preview()
    return file_url
