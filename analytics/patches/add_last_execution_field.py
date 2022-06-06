import frappe


def execute():
    if not frappe.db.a_row_exists("Query"):
        return

    Query = frappe.qb.DocType("Query")
    frappe.qb.update(Query).set(Query.last_execution, Query.modified).run()
