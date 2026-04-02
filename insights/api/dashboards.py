import frappe

from insights.decorators import insights_whitelist, validate_type


@insights_whitelist()
def get_dashboards(search_term: str | None = None, limit: int = 50, get_favorites: bool = False):
    dashboards = frappe.get_list(
        "Insights Dashboard v3",
        or_filters={
            "name": ["like", f"%{search_term}%" if search_term else "%"],
            "title": ["like", f"%{search_term}%" if search_term else "%"],
        },
        filters={"_liked_by": ["like", f"%{frappe.session.user}%"]} if get_favorites else {},
        fields=[
            "name",
            "title",
            "workbook",
            "creation",
            "modified",
            "preview_image",
            "items",
            "_liked_by",
        ],
        order_by="creation desc",
        limit=limit if not get_favorites else 0,
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
        if dashboard._liked_by:
            dashboard["is_favourite"] = frappe.session.user in frappe.as_json(dashboard._liked_by)
        del dashboard["items"]

    return dashboards


@insights_whitelist()
@validate_type
def update_dashboard_preview(dashboard_name: str):
    dashboard = frappe.get_doc("Insights Dashboard v3", dashboard_name)
    file_url = dashboard.generate_dashboard_preview()
    return file_url
