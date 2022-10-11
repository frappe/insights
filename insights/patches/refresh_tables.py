# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
    data_sources = frappe.get_all(
        "Insights Data Source",
        filters={"status": "Active", "name": ["!=", "Demo Data"]},
    )
    for data_source in data_sources:
        data_source = frappe.get_doc("Insights Data Source", data_source.name)
        data_source.connector.create_insights_tables(force=True)
        data_source.save()
        frappe.db.commit()
