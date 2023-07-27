import frappe


def execute():
    """delete_unused_query_based_tables"""

    # get all insights tables
    insights_tables = frappe.get_all(
        "Insights Table", filters={"is_query_based": 1}, fields=["name", "table"]
    )

    # get all generate sqls
    generated_sqls = frappe.get_all("Insights Query", pluck="sql")

    # delete insights table if `table` not present in any sql
    for table in insights_tables:
        for sql in generated_sqls:
            if sql and table.table in sql:
                break
        else:
            frappe.delete_doc("Insights Table", table.name)
