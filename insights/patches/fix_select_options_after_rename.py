# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe


def execute():
    # when the doctype Query was renamed, the options like "Permission Query" in Server Script was renamed to "Permission Insights Query"
    # this patch fixes the options in the docfields
    frappe.db.sql(
        "update `tabDocField` set `options` = replace(`options`, 'Insights ', '') where fieldtype = 'Select' and options like '%Insights %'"
    )

    frappe.db.sql(
        "update `tabCustom Field` set `options` = replace(`options`, 'Insights ', '') where fieldtype = 'Select' and options like '%Insights %'"
    )

    frappe.db.sql(
        "update `tabProperty Setter` set `value` = replace(`value`, 'Insights ', '') where property = 'options' and value like '%Insights %'"
    )
