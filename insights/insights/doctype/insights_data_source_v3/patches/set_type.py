import frappe


def execute():
    frappe.db.set_value(
        "Insights Data Source v3",
        {"type": ["is", "not set"]},
        "type",
        "Database",
        update_modified=False,
    )
