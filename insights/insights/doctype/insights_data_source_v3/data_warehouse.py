import os
from datetime import datetime

import frappe
import frappe.utils
import ibis
from frappe.utils import get_files_path
from ibis import BaseBackend
from ibis.expr.types import Table as IbisTable

from insights.insights.doctype.insights_table_column.insights_table_column import (
    InsightsTableColumn,
)

WAREHOUSE_DB_NAME = "insights.duckdb"


class DataWarehouse:
    def __init__(self):
        self.warehouse_path = get_warehouse_folder_path()
        self.db_path = os.path.join(self.warehouse_path, WAREHOUSE_DB_NAME)

    @property
    def db(self) -> BaseBackend:
        if not os.path.exists(self.db_path):
            ddb = ibis.duckdb.connect(self.db_path)
            ddb.disconnect()

        if WAREHOUSE_DB_NAME not in frappe.local.insights_db_connections:
            ddb = ibis.duckdb.connect(self.db_path, read_only=True)
            frappe.local.insights_db_connections[WAREHOUSE_DB_NAME] = ddb

        return frappe.local.insights_db_connections[WAREHOUSE_DB_NAME]

    def get_table(self, data_source, table_name, sync=False, use_live_connection=True):
        if use_live_connection:
            return self.get_remote_table(data_source, table_name)
        else:
            return self.get_warehouse_table(data_source, table_name, sync)

    def get_warehouse_table(self, data_source, table_name, sync=False):
        parquet_file = get_parquet_filepath(data_source, table_name)
        warehouse_table = get_warehouse_table_name(data_source, table_name)

        if not os.path.exists(parquet_file):
            if sync:
                self.create_parquet_file(data_source, table_name)
                return self.db.read_parquet(parquet_file, table_name=warehouse_table)
            else:
                frappe.throw(
                    f"{table_name} of {data_source} is not synced to the data warehouse."
                )

        if not self.db.list_tables(warehouse_table):
            return self.db.read_parquet(parquet_file, table_name=warehouse_table)
        else:
            return self.db.table(warehouse_table)

    def get_remote_table(self, data_source, table_name):
        ds = frappe.get_doc("Insights Data Source v3", data_source)
        remote_db = ds._get_ibis_backend()
        return remote_db.table(table_name)

    def create_parquet_file(self, data_source, table_name):
        path = get_parquet_filepath(data_source, table_name)
        if os.path.exists(path):
            print(
                f"Skipping creation of parquet file for {table_name} of {data_source} as it already exists. "
                "Skipping insights table creation as well."
            )
            return

        ds = frappe.get_doc("Insights Data Source v3", data_source)
        remote_db = ds._get_ibis_backend()
        table = remote_db.table(table_name)

        if ds.is_frappe_db and hasattr(table, "creation"):
            first_day_of_last_year = datetime.now().replace(
                month=1, day=1, year=datetime.now().year - 1
            )
            table = table.filter(table.creation >= first_day_of_last_year)

        table.to_parquet(path, compression="snappy")

    def sync_insights_table(self, data_source, table_name, table: IbisTable):
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
            sync_insights_table,
        )

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
