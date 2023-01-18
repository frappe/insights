# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query Table"):
        return

    QueryTable = frappe.qb.DocType("Insights Query Table")

    query = (
        frappe.qb.from_(QueryTable)
        .select(QueryTable.join, QueryTable.name)
        .where(QueryTable.join.like("%condition%"))
    )
    tables = query.run(as_dict=True)
    for table in tables:
        join = frappe.parse_json(table.join)
        if join.get("condition"):
            condition = join.get("condition").get("value")
            if not condition:
                continue
            left = condition.split("=")[0].strip()
            right = condition.split("=")[1].strip()
            if not left or not right:
                continue
            join["condition"] = {
                "left": {
                    "value": left,
                    "label": left,
                },
                "right": {
                    "value": right,
                    "label": right,
                },
            }
            frappe.db.set_value(
                "Insights Query Table", table.name, "join", frappe.as_json(join)
            )
