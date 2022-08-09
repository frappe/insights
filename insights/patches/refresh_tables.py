# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
    data_sources = frappe.get_all("Data Source")
    for data_source in data_sources:
        data_source = frappe.get_doc("Data Source", data_source.name)
        data_source.import_tables(refresh_links=True)
        frappe.db.commit()
