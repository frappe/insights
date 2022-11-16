import frappe

from insights.insights.doctype.insights_data_source.sources.query_store import (
    sync_query_store,
)


def execute():
    if not frappe.db.a_row_exists("Insights Query"):
        return

    Query = frappe.qb.DocType("Insights Query")
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
        (
            frappe.qb.update(Query)
            .set(Query.is_stored, 1)
            .where(Query.name.isin(queries_to_stored))
            .run()
        )
        sync_query_store(tables=queries_to_stored, force=True)
