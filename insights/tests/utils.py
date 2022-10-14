# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe


def create_insights_query(title, data_source):
    query = frappe.new_doc("Insights Query")
    query.title = title or "Test Query"
    query.data_source = data_source
    query.save()
    return query
