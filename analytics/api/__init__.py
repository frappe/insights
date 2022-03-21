# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.query_builder import Criterion, DocType
from frappe.query_builder.functions import Count

from analytics.analytics.doctype.query.utils import Operations


@frappe.whitelist()
def get_column_list(tables):
    if not isinstance(tables, list):
        return []

    column_list = []
    for table in tables:
        meta = frappe.get_meta(table)
        if not meta:
            continue

        valid_columns = meta.get_valid_columns()
        column_list.append(
            {"label": "Name", "name": "name", "type": "Data", "table": table}
        )
        for d in meta.get("fields"):
            if d.fieldname not in valid_columns:
                continue
            column_list.append(
                {
                    "label": d.label,
                    "name": d.fieldname,
                    "type": d.fieldtype,
                    "table": d.parent,
                }
            )

    return column_list


@frappe.whitelist()
def get_table_list(search_term=""):
    filters = {"issingle": 0}
    if search_term:
        filters = {"name": ["like", f"%{search_term}%"]}

    return frappe.get_all(
        "DocType", filters=filters, fields=["name as label"], limit=20
    )


@frappe.whitelist()
def get_operator_list(fieldtype):
    return [
        {"label": "Equals", "value": "="},
    ]


@frappe.whitelist()
def fetch_query_result(tables, columns, filters):
    tables, columns, filters = sanitize_data(tables, columns, filters)

    if not tables or not columns:
        return

    query = generate_query(tables, columns, filters)

    result, error = [], None
    try:
        result = query.run(as_dict=True)
    except Exception as e:
        error = str(e)

    return {
        "error": error,
        "data": result,
        "query": query.get_sql(),
        "columns": [c.get("label") for c in columns],
    }


def sanitize_data(tables, columns, filters):
    if isinstance(tables, str):
        tables = json.loads(tables)

    if isinstance(columns, str):
        columns = json.loads(columns)

    if isinstance(filters, str):
        filters = json.loads(filters)

    return tables, columns, filters


def generate_query(tables, columns, filters):
    query = frappe.qb

    for table in tables:
        query = query.from_(table.get("label"))

    for column in columns:
        Table = DocType(column.get("table"))
        Field = Table[column.get("name")]

        if column.get("aggregation") != "Group By":
            if column.get("aggregation") == "Count":
                Field = Count(Field)

            AliasedField = Field.as_(column.get("label"))
            query = query.select(AliasedField)

            if column.get("aggregation") == "Distinct":
                query = query.distinct()
        else:
            AliasedField = Field.as_(column.get("label"))
            query = query.select(AliasedField)
            query = query.groupby(Field)

    def apply_filters(filters, query):
        _conditions = []
        for condition in filters.get("conditions"):
            if condition.get("group_operator"):
                query = apply_filters(condition, query)
                continue

            LeftTable = DocType(condition.get("left_table"))
            LeftField = LeftTable[condition.get("left_value")]
            operation = Operations.get_operation(condition.get("operator_value"))
            expression = operation(LeftField, condition.get("right"))
            _conditions.append(expression)

        if filters.get("group_operator") == "All":
            query = query.where(Criterion.all(_conditions))
        elif filters.get("group_operator") == "Any":
            query = query.where(Criterion.any(_conditions))

        return query

    if filters:
        query = apply_filters(filters, query)

    return query
