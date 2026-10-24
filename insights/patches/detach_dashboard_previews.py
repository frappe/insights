import frappe

from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import PREVIEW_FILE_SUFFIX

DASHBOARD = "Insights Dashboard v3"


def execute():
    """Detach preview files from the documents they were attached to.

    Frappe lets every reader of a document download its attachments, and a
    preview shows the rows of the user it was rendered for. Insights before v3.50
    attached them to the workbook, later to the dashboard.
    `get_dashboard_preview` serves them now. A file that is not its
    dashboard's current preview goes: Frappe saves identical content once, so
    a dashboard can point at another's file, and an app's dashboard kept its
    file after its preview was cleared.
    """
    previews = {}
    for dashboard in frappe.get_all(
        DASHBOARD, filters={"preview_image": ["is", "set"]}, fields=["name", "preview_image"]
    ):
        file_url = dashboard.preview_image.partition("?")[0]
        if file_url == f"/private/files/{dashboard.name}{PREVIEW_FILE_SUFFIX}":
            previews[file_url] = dashboard.name
        else:
            frappe.db.set_value(DASHBOARD, dashboard.name, "preview_image", None, update_modified=False)

    kept = set()
    for file in frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": ["in", [DASHBOARD, "Insights Workbook"]],
            "file_name": ["like", f"%{PREVIEW_FILE_SUFFIX}"],
        },
        fields=["name", "file_url", "is_private"],
        order_by="creation asc",
    ):
        if file.is_private and file.file_url in previews and file.file_url not in kept:
            kept.add(file.file_url)
            frappe.db.set_value(
                "File",
                file.name,
                {"attached_to_doctype": None, "attached_to_name": None, "owner": "Administrator"},
                update_modified=False,
            )
        else:
            frappe.delete_doc("File", file.name, ignore_permissions=True)
