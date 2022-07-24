import json
import frappe


def execute():
    if not frappe.db.a_row_exists("Query"):
        return

    Query = frappe.qb.DocType("Query")
    default_filters = json.dumps(
        {
            "type": "LogicalExpression",
            "operator": "&&",
            "level": 1,
            "position": 1,
            "conditions": [],
        },
        indent=2,
    )
    frappe.qb.update(Query).set(Query.filters, default_filters).run()
