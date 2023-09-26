import frappe

from insights.api.permissions import is_private
from insights.api.telemetry import track
from insights.decorators import check_role
from insights.insights.doctype.insights_team.insights_team import (
    get_allowed_resources_for_user,
    get_permission_filter,
)


@frappe.whitelist()
@check_role("Insights User")
def get_dashboard_list():
    dashboards = frappe.get_list(
        "Insights Dashboard",
        filters={**get_permission_filter("Insights Dashboard")},
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
            filters={"reference_doctype": "Insights Dashboard", "reference_name": dashboard.name},
        )

        dashboard["is_private"] = is_private("Insights Dashboard", dashboard.name)

    return dashboards


@frappe.whitelist()
@check_role("Insights User")
def create_dashboard(title):
    track("create_dashboard")
    dashboard = frappe.get_doc({"doctype": "Insights Dashboard", "title": title})
    dashboard.insert()
    return {
        "name": dashboard.name,
        "title": dashboard.title,
    }


@frappe.whitelist()
@check_role("Insights User")
def get_dashboard_options(chart):
    allowed_dashboards = get_allowed_resources_for_user("Insights Dashboard")
    if not allowed_dashboards:
        return []

    # find all dashboards that don't have the chart within the allowed dashboards
    Dashboard = frappe.qb.DocType("Insights Dashboard")
    DashboardItem = frappe.qb.DocType("Insights Dashboard Item")

    return (
        frappe.qb.from_(Dashboard)
        .left_join(DashboardItem)
        .on(Dashboard.name == DashboardItem.parent)
        .select(Dashboard.name.as_("value"), Dashboard.title.as_("label"))
        .where(Dashboard.name.isin(allowed_dashboards) & (DashboardItem.chart != chart))
        .groupby(Dashboard.name)
        .run(as_dict=True)
    )


@frappe.whitelist()
def add_chart_to_dashboard(dashboard, chart):
    dashboard = frappe.get_doc("Insights Dashboard", dashboard)
    dashboard.add_chart(chart)
    dashboard.save()
