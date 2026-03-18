# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Migrates legacy flat warehouse tables stored as "scrub_data_source.scrub_table" in the
# main DuckDB schema to proper per-data-source schemas: schema.table_name

import os
from contextlib import suppress

import frappe


def execute():
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

    with w.get_write_connection() as db:
        for row in stored_tables:
            schema = get_warehouse_schema_name(row.data_source)
            table = frappe.scrub(row.table)
            legacy_name = f"{frappe.scrub(row.data_source)}.{table}"

            with suppress(Exception):
                db.create_database(schema)

            with suppress(Exception):
                expr = db.table(legacy_name)
                db.create_table(table, expr, database=schema, overwrite=True)
                db.drop_table(legacy_name, force=True)
                frappe.logger().info(f"Insights warehouse: migrated '{legacy_name}' → '{schema}'.'{table}'")
