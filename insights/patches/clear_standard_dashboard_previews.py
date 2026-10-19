import frappe


def execute():
    """Clear the previews rendered for an app's dashboards.

    They show the rows of whoever rendered them to every role the dashboard
    ships to. `generate_dashboard_preview` no longer renders them.
    """
    workbooks = frappe.get_all("Insights Workbook", filters={"is_standard": 1}, pluck="name")
    if not workbooks:
        return
    for dashboard in frappe.get_all(
        "Insights Dashboard v3",
        filters={"workbook": ["in", workbooks], "preview_image": ["is", "set"]},
        pluck="name",
    ):
        frappe.db.set_value("Insights Dashboard v3", dashboard, "preview_image", None, update_modified=False)
