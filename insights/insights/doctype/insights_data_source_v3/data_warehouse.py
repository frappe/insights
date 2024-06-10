import os

import frappe
import ibis
from frappe.utils import get_files_path
from ibis import BaseBackend

from insights.insights.doctype.insights_table_column.insights_table_column import (
    InsightsTableColumn,
)


class DataWarehouse:
    def __init__(self):
        self.warehouse_path = get_warehouse_folder_path()
        self.db_path = os.path.join(self.warehouse_path, "insights.duckdb")

    @property
    def db(self) -> BaseBackend:
        if not hasattr(frappe.local, "insights_warehouse"):
            frappe.local.insights_warehouse = ibis.duckdb.connect(self.db_path)
        return frappe.local.insights_warehouse

    def get_table(self, data_source, table_name, sync=False):
        parquet_file = get_parquet_filepath(data_source, table_name)
        if not os.path.exists(parquet_file):
            if sync:
                self.create_parquet_file(data_source, table_name)
            else:
                frappe.throw(
                    f"{table_name} of {data_source} is not synced to the data warehouse."
                )

        warehouse_table = get_warehouse_table_name(data_source, table_name)
        if not self.db.list_tables(warehouse_table):
            return self.db.read_parquet(parquet_file, table_name=warehouse_table)
        else:
            if sync:
                return self.db.read_parquet(parquet_file, table_name=warehouse_table)
            else:
                return self.db.table(warehouse_table)

    def create_parquet_file(self, data_source, table_name):

        from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
            sync_insights_table,
        )

        path = get_parquet_filepath(data_source, table_name)
        if os.path.exists(path):
            print(
                f"Skipping creation of parquet file for {table_name} of {data_source} as it already exists. "
                "Skipping insights table creation as well."
            )
            return

        ds = frappe.get_doc("Insights Data Source v3", data_source)
        with ds._get_ibis_backend() as remote_db:
            table = remote_db.table(table_name)
            # TODO: check metadata to see if copy is needed
            table.to_parquet(path, compression="snappy")

        columns = InsightsTableColumn.from_ibis_schema(table.schema())
        sync_insights_table(data_source, table_name, columns=columns)


def get_warehouse_folder_path():
    path = os.path.realpath(get_files_path(is_private=1))
    path = os.path.join(path, "insights_data_warehouse")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_warehouse_table_name(data_source, table_name):
    return f"{frappe.scrub(data_source)}.{frappe.scrub(table_name)}"


def get_parquet_filepath(data_source, table_name):
    warehouse_path = get_warehouse_folder_path()
    warehouse_table = get_warehouse_table_name(data_source, table_name)
    return os.path.join(warehouse_path, f"{warehouse_table}.parquet")


def close_warehouse_connection():
    if hasattr(frappe.local, "insights_warehouse"):
        frappe.local.insights_warehouse.disconnect()
        del frappe.local.insights_warehouse
