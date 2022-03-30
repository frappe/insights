# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from pypika import CustomFunction


@frappe.whitelist()
def get_queries():
    Query = frappe.qb.DocType("Query")
    QueryTable = frappe.qb.DocType("Query Table")
    GroupConcat = CustomFunction("Group_Concat", ["column"])
    return (
        frappe.qb.from_(Query)
        .join(QueryTable)
        .on(Query.name == QueryTable.parent)
        .select(Query.name, Query.title, GroupConcat(QueryTable.label).as_("tables"))
        .groupby(Query.name)
    ).run(as_dict=True, debug=1)


@frappe.whitelist()
def get_operator_list(fieldtype):
    return [
        {"label": "equals", "value": "="},
    ]


@frappe.whitelist()
def get_aggregation_list():
    return ["Count", "Sum"]
