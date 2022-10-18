import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    Query = frappe.qb.DocType("Insights Query")
    frappe.qb.update(Query).set(Query.is_stored, 1).where(
        Query.data_source == "Query Store"
    ).run()

    queries_on_query_store = frappe.get_all(
        "Insights Query", filters={"data_source": "Query Store"}, pluck="name"
    )

    queries_to_stored = []
    for query in queries_on_query_store:
        tables = frappe.get_all(
            "Insights Query Table", filters={"parent": query}, pluck="table"
        )
        for table in tables:
            if frappe.db.exists("Insights Query", table):
                queries_to_stored.append(table)

    if queries_to_stored:
        query_store = frappe.get_doc("Insights Data Source", "Query Store")
        query_store.sync_tables(queries=queries_to_stored)
