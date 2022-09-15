import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    Query = frappe.qb.DocType("Insights Query")
    frappe.qb.update(Query).set(Query.last_execution, Query.modified).run()
