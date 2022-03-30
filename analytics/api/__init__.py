# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_operator_list(fieldtype):
    return [
        {"label": "equals", "value": "="},
    ]


@frappe.whitelist()
def get_aggregation_list():
    return ["Count", "Sum"]
