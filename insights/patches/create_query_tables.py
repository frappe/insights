import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    if not frappe.db.exists("Insights Data Source", "Query Store"):
        frappe.get_doc(
            {
                "status": "Active",
                "name": "Query Store",
                "title": "Query Store",
                "database_type": "MariaDB",
                "doctype": "Insights Data Source",
                "modified": "2022-01-01 00:01:00.000000",
                "creation": "2022-01-01 00:01:00.000000",
            }
        ).insert()

    for query_name in frappe.get_all("Insights Query", pluck="name"):
        query = frappe.get_doc("Insights Query", query_name)
        query.update_query_table()
