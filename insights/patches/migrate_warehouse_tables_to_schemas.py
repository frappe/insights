# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Migrates legacy flat warehouse tables stored as "scrub_data_source.scrub_table" in the
# main DuckDB schema to proper per-data-source schemas: schema.table_name

import os
from contextlib import suppress

import frappe


def execute():
    from duckdb import CatalogException
    from ibis.common.exceptions import TableNotFound

    from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
        Warehouse,
        get_warehouse_schema_name,
    )

    w = Warehouse()

    if not os.path.exists(w.get_db_path()):
        return

    stored_tables = frappe.get_all(
        "Insights Table v3",
        filters={"stored": 1},
        fields=["data_source", "table"],
    )

    if not stored_tables:
        return

    logger = frappe.logger()

    with w.get_write_connection() as db:
        for row in stored_tables:
            schema = get_warehouse_schema_name(row.data_source)
            table = frappe.scrub(row.table)
            legacy_name = f"{frappe.scrub(row.data_source)}.{table}"

            # CatalogException is raised when the schema already exists — that is fine.
            with suppress(CatalogException):
                db.create_database(schema)

            # TableNotFound means the legacy table was never written; skip silently.
            try:
                expr = db.table(legacy_name)
                db.create_table(table, expr, database=schema, overwrite=True)
                db.drop_table(legacy_name, force=True)
                logger.info(f"Insights warehouse: migrated '{legacy_name}' → '{schema}'.'{table}'")
            except TableNotFound:
                logger.warning(f"Insights warehouse: legacy table '{legacy_name}' not found, skipping.")
            except Exception:
                logger.exception(
                    f"Insights warehouse: failed to migrate '{legacy_name}' → '{schema}'.'{table}'. "
                    "Manual remediation may be required."
                )
