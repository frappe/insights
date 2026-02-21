# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsChart(Document):
    pass


def get_chart_public_key(name:str):

    if not frappe.db.exists("Insights Chart", name):
        frappe.throw("Chart not found")

    is_public = frappe.db.get_value("Insights Chart", name, "is_public")
    if not is_public:
        frappe.throw("Chart is not public")
        return

    existing_key = frappe.db.get_value("Insights Chart", name, "public_key", cache=True)
    if existing_key:
        return existing_key

    public_key = frappe.generate_hash()
    frappe.db.set_value("Insights Chart", name, "public_key", public_key)
    return public_key
