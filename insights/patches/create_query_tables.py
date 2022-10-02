import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    for query_name in frappe.get_all("Insights Query", pluck="name"):
        query = frappe.get_doc("Insights Query", query_name)
        query.update_query_table()
