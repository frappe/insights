# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from pypika import CustomFunction


@frappe.whitelist()
def get_data_sources():
    return frappe.get_all("Data Source", pluck="name")


@frappe.whitelist()
def get_queries():
    Query = frappe.qb.DocType("Query")
    QueryTable = frappe.qb.DocType("Query Table")
    GroupConcat = CustomFunction("Group_Concat", ["column"])
    return (
        frappe.qb.from_(Query)
        .left_join(QueryTable)
        .on(Query.name == QueryTable.parent)
        .select(
            Query.name,
            Query.title,
            GroupConcat(QueryTable.label).as_("tables"),
            Query.data_source,
            Query.modified,
        )
        .groupby(Query.name)
        .orderby(Query.modified, order=frappe.qb.desc)
    ).run(as_dict=True)


@frappe.whitelist()
def create_query(title, data_source):
    query = frappe.new_doc("Query")
    query.title = title
    query.data_source = data_source
    query.save()
    return query.name


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
def get_column_menu_options(fieldtype):
    aggregation_options = []
    format_options = []

    text_data_types = ("char", "varchar", "enum", "text", "longtext")
    number_data_types = ("int", "decimal", "bigint", "float", "double")
    datetime_data_types = ("datetime", "timestamp")
    date_data_types = "date"

    fieldtype = fieldtype.lower()
    if fieldtype in text_data_types:
        aggregation_options = [
            {"label": "Group By", "value": "Group By"},
            {"label": "Count of all", "value": "Count"},
            {"label": "Count of distinct", "value": "Count Distinct"},
            {"label": "Minimum", "value": "Min"},
            {"label": "Maximum", "value": "Max"},
        ]
    if fieldtype in number_data_types:
        aggregation_options = [
            {"label": "Group By", "value": "Group By"},
            {"label": "Count of all", "value": "Count"},
            {"label": "Count of distinct", "value": "Count Distinct"},
            {"label": "Sum", "value": "Sum"},
            {"label": "Minimum", "value": "Min"},
            {"label": "Maximum", "value": "Max"},
            {"label": "Average", "value": "Avg"},
        ]

    if fieldtype in datetime_data_types:
        aggregation_options = [
            {"label": "Group By", "value": "Group By"},
            {"label": "Count of all", "value": "Count"},
            {"label": "Count of distinct", "value": "Count Distinct"},
            {"label": "Minimum", "value": "Min"},
            {"label": "Maximum", "value": "Max"},
        ]
        format_options = [
            {"label": "Minute", "value": "Minute"},
            {"label": "Hour", "value": "Hour"},
            {"label": "Day", "value": "Day"},
            {"label": "Month", "value": "Month"},
            {"label": "Year", "value": "Year"},
            {"label": "Minute of Hour", "value": "Minute of Hour"},
            {"label": "Hour of Day", "value": "Hour of Day"},
            {"label": "Day of Week", "value": "Day of Week"},
            {"label": "Day of Month", "value": "Day of Month"},
            {"label": "Day of Year", "value": "Day of Year"},
            {"label": "Month of Year", "value": "Month of Year"},
            {"label": "Quarter of Year", "value": "Quarter of Year"},
        ]

    if fieldtype in date_data_types:
        aggregation_options = [
            {"label": "Group By", "value": "Group By"},
            {"label": "Count of all", "value": "Count"},
            {"label": "Count of distinct", "value": "Count Distinct"},
            {"label": "Minimum", "value": "Min"},
            {"label": "Maximum", "value": "Max"},
        ]
        format_options = [
            {"label": "Year", "value": "Year"},
            {"label": "Month", "value": "Month"},
            {"label": "Day", "value": "Day"},
            {"label": "Quarter of Year", "value": "Quarter of Year"},
            {"label": "Month of Year", "value": "Month of Year"},
            {"label": "Day of Year", "value": "Day of Year"},
            {"label": "Day of Month", "value": "Day of Month"},
            {"label": "Day of Week", "value": "Day of Week"},
        ]

    return {
        "aggregation_options": aggregation_options,
        "format_options": format_options,
    }


@frappe.whitelist()
def create_query_chart(query, title, type, label_column, value_column):
    chart = frappe.new_doc("Query Chart")
    chart.title = title
    chart.query = query
    chart.type = type
    chart.label_column = label_column
    chart.value_column = value_column
    chart.save()


@frappe.whitelist()
def update_query_chart(chart_name, title, type, label_column, value_column):
    chart = frappe.get_doc("Query Chart", chart_name)
    chart.title = title
    chart.type = type
    chart.label_column = label_column
    chart.value_column = value_column
    chart.save()


@frappe.whitelist()
def get_query_chart(query):
    if chart_name := frappe.db.exists("Query Chart", {"query": query}):
        chart = frappe.get_doc("Query Chart", chart_name)
        return {
            "name": chart.name,
            "query": chart.query,
            "title": chart.title,
            "type": chart.type,
            "label_column": chart.label_column,
            "value_column": chart.value_column,
        }
