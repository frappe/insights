import frappe
from frappe import _

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
            "folder",
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
def get_dashboard_folders():
    return frappe.get_all(
        "Insights Folder",
        filters={"type": "dashboard"},
        fields=["name", "title", "sort_order"],
        order_by="sort_order asc, creation asc",
    )


@insights_whitelist()
def create_dashboard_folder(title: str):
    folder = frappe.new_doc("Insights Folder")
    folder.title = title
    folder.type = "dashboard"
    folder.sort_order = frappe.db.count("Insights Folder", filters={"type": "dashboard"})
    folder.insert()
    return folder.as_dict()


def get_dashboard_folder(folder_name: str):
    folder = frappe.get_doc("Insights Folder", folder_name)
    if folder.type != "dashboard":
        frappe.throw(_("Invalid dashboard folder"))
    return folder


@insights_whitelist()
def rename_dashboard_folder(folder_name: str, title: str):
    folder = get_dashboard_folder(folder_name)
    folder.check_permission("write")
    folder.title = title
    folder.save()
    return folder.as_dict()


@insights_whitelist()
def delete_dashboard_folder(folder_name: str):
    folder = get_dashboard_folder(folder_name)
    folder.check_permission("delete")
    frappe.db.set_value(
        "Insights Dashboard v3",
        {"folder": folder_name},
        "folder",
        None,
        update_modified=False,
    )
    folder.delete()


@insights_whitelist()
def move_dashboard_to_folder(dashboard_name: str, folder_name: str | None = None):
    dashboard = frappe.get_doc("Insights Dashboard v3", dashboard_name)
    dashboard.check_permission("write")
    if folder_name:
        get_dashboard_folder(folder_name).check_permission("read")
    dashboard.db_set("folder", folder_name, update_modified=False)


@insights_whitelist()
def update_dashboard_folder_order(folder_names: list[str]):
    for sort_order, folder_name in enumerate(folder_names):
        folder = get_dashboard_folder(folder_name)
        folder.check_permission("write")
        folder.db_set("sort_order", sort_order, update_modified=False)


@insights_whitelist()
@validate_type
def update_dashboard_preview(dashboard_name: str):
    dashboard = frappe.get_doc("Insights Dashboard v3", dashboard_name)
    file_url = dashboard.generate_dashboard_preview()
    return file_url
