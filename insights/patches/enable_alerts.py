import frappe


def execute():
    if frappe.db.exists("Insights Alert", {"disabled": 0}):
        frappe.db.set_single_value("Insights Settings", "enable_alerts", 1)
