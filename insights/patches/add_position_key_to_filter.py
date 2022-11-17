import json

import frappe
from frappe.utils import cstr


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    queries = frappe.get_all("Insights Query", fields=["name", "filters"])

    for query in queries:
        _filters = json.loads(query.get("filters"))
        set_default_position(_filters)
        _filters = json.dumps(_filters, indent=2, default=cstr)
        frappe.db.set_value(
            "Query", query.get("name"), "filters", _filters, update_modified=False
        )


def set_default_position(filters):
    if "conditions" not in filters:
        return

    filters["position"] = filters.get("position") or 1
    for condition in filters.get("conditions"):
        set_default_position(condition)
