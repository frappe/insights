import frappe


def execute():
    # migrate does not write a new Single field's default, and 0 means no limit
    if not frappe.db.exists("Singles", {"doctype": "Insights Settings", "field": "max_export_rows"}):
        frappe.db.set_single_value("Insights Settings", "max_export_rows", 100_000)
