import frappe

from insights.insights.doctype.insights_table_v3.table_rename import rename_tables


def execute():
    """
    Postgres data sources used to qualify every table name with its schema
    ("public.tabSales Invoice") even when only one schema was configured. The prefix
    leaked into the UI and broke the table -> doctype mapping for frappe databases, so
    executing any query against a postgres Site DB failed with a `DoesNotExistError`
    (frappe/insights#1195).

    Table names are now only qualified when the data source spans several schemas. This
    patch strips the redundant prefix from everything that stored it.
    """
    sources = frappe.get_all(
        "Insights Data Source v3",
        filters={"database_type": "PostgreSQL"},
        fields=["name", "schema"],
    )

    for source in sources:
        schemas = [s.strip() for s in (source.schema or "").split(",") if s.strip()] or ["public"]
        if len(schemas) > 1:
            # names are still qualified for multi schema sources
            continue

        try:
            unqualify_source(source.name, f"{schemas[0]}.")
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title=f"Failed to strip schema prefix for {source.name}")


def unqualify_source(data_source: str, prefix: str) -> None:
    tables = frappe.get_all(
        "Insights Table v3",
        filters={"data_source": data_source, "table": ["like", f"{prefix}%"]},
        pluck="table",
    )
    rename_tables(data_source, {table: table[len(prefix) :] for table in tables})
