import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    QueryColumn = frappe.qb.DocType("Insights Query Column")
    (
        frappe.qb.update(QueryColumn)
        .set(QueryColumn.column, "*")
        .where(QueryColumn.column == "count")
        .run()
    )
