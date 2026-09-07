# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import after_request
from insights.insights.doctype.insights_table_v3.insights_table_v3 import store_columns
from insights.utils import InsightsDataSourcev3


def execute():
    """Write down the columns of every table synced before the sync recorded them.

    Without this, column search sees only the tables synced after the upgrade.
    Reading a table's shape needs the source, so this is one connection per table
    and it runs once.
    """
    tables = frappe.get_all(
        "Insights Table v3",
        filters={"columns": ["is", "not set"]},
        fields=["name", "data_source", "table"],
        order_by="data_source",
    )

    for table in tables:
        try:
            data_source = InsightsDataSourcev3.get_doc(table.data_source)
            store_columns(table.data_source, table.table, data_source.get_ibis_table(table.table).schema())
        except Exception:
            print(f"Could not read the columns of {table.table} of {table.data_source}")
            frappe.db.rollback()
        finally:
            frappe.db.commit()

    after_request()
