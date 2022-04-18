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
    operator_list = []
    text_data_types = ("char", "varchar", "enum", "text", "longtext")
    number_data_types = ("int", "decimal", "bigint", "float", "double")
    date_data_types = ("date", "datetime", "time", "timestamp")

    fieldtype = fieldtype.lower()
    if fieldtype in text_data_types:
        operator_list += [
            {"label": "equals", "value": "="},
            {"label": "not equals", "value": "!="},
            {"label": "contains", "value": "like"},
            {"label": "not contains", "value": "not like"},
            {"label": "in", "value": "in"},
            {"label": "not in", "value": "not in"},
            {"label": "is set", "value": "is set"},
            {"label": "is not set", "value": "is not set"},
        ]
    if fieldtype in number_data_types:
        operator_list = [
            {"label": "equals", "value": "="},
            {"label": "not equals", "value": "!="},
            {"label": "in", "value": "in"},
            {"label": "not in", "value": "not in"},
            {"label": "is set", "value": "is set"},
            {"label": "is not set", "value": "is not set"},
            {"label": "greater than", "value": ">"},
            {"label": "smaller than", "value": "<"},
            {"label": "greater than equal to", "value": ">="},
            {"label": "smaller than equal to", "value": "<="},
            {"label": "between", "value": "between"},
        ]

    if fieldtype in date_data_types:
        operator_list = [
            {"label": "equals", "value": "="},
            {"label": "not equals", "value": "!="},
            {"label": "is set", "value": "is set"},
            {"label": "is not set", "value": "is not set"},
            {"label": "greater than", "value": ">"},
            {"label": "smaller than", "value": "<"},
            {"label": "greater than equal to", "value": ">="},
            {"label": "smaller than equal to", "value": "<="},
            {"label": "between", "value": "between"},
        ]

    return operator_list


@frappe.whitelist()
def get_aggregation_list():
    return ["Count", "Sum"]
