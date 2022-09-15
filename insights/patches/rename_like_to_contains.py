import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    queries = frappe.get_all("Insights Query", fields=["name", "filters"])

    for query in queries:
        new_filter = query.filters.replace("like", "contains")
        frappe.db.set_value(
            "Query", query.name, "filters", new_filter, update_modified=False
        )
