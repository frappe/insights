import frappe


def execute():
    if frappe.db.exists("Insights Table v3", {"stored": 1}):
        frappe.db.set_single_value("Insights Settings", "enable_data_store", 1)
