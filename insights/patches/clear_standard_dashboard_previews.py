import frappe


def execute():
    """Clear the previews rendered for an app's dashboards, and delete their files.

    They show the rows of whoever rendered them to every role the dashboard
    ships to. `generate_dashboard_preview` no longer renders them.
    """
    workbooks = frappe.get_all("Insights Workbook", filters={"is_standard": 1}, pluck="name")
    if not workbooks:
        return
    for dashboard in frappe.get_all(
        "Insights Dashboard v3",
        filters={"workbook": ["in", workbooks], "preview_image": ["is", "set"]},
        fields=["name", "preview_image"],
    ):
        # the stored url ends in a query string that defeats the browser cache
        for file in frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Insights Dashboard v3",
                "attached_to_name": dashboard.name,
                "file_url": dashboard.preview_image.split("?")[0],
            },
            pluck="name",
        ):
            frappe.delete_doc("File", file, ignore_permissions=True)
        frappe.db.set_value(
            "Insights Dashboard v3", dashboard.name, "preview_image", None, update_modified=False
        )
