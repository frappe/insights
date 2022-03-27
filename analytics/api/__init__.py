# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


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
            {"label": "Name", "column_name": "name", "type": "Data", "table": table}
        )
        for d in meta.get("fields"):
            if d.fieldname not in valid_columns:
                continue
            column_list.append(
                {
                    "label": d.label,
                    "column_name": d.fieldname,
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
def get_aggregation_list():
    return ["Count", "Sum"]
