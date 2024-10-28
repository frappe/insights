import os

import frappe
import frappe.utils
import ibis
from frappe.utils import get_files_path
from ibis import BaseBackend, _
from ibis.expr.types import Expr

from insights.utils import InsightsDataSourcev3, InsightsTablev3

WAREHOUSE_DB_NAME = "insights.duckdb"


class Warehouse:
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

    def get_table(self, data_source: str, table_name: str) -> "WarehouseTable":
        return WarehouseTable(data_source, table_name)


class WarehouseTable:
    def __init__(self, data_source: str, table_name: str):
        self.warehouse = Warehouse()
        self.data_source = data_source
        self.table_name = table_name
        self.warehouse_table_name = get_warehouse_table_name(data_source, table_name)
        self.parquet_filepath = get_parquet_filepath(data_source, table_name)

    def get_ibis_table(self, import_if_not_exists: bool = True) -> Expr:
        if not os.path.exists(self.parquet_filepath):
            if import_if_not_exists:
                self.import_remote_table()
                return self.warehouse.db.read_parquet(
                    self.parquet_filepath, table_name=self.warehouse_table_name
                )
            else:
                frappe.throw(
                    f"{self.table_name} of {self.data_source} is not imported to the data warehouse."
                )

        if not self.warehouse.db.list_tables(self.warehouse_table_name):
            return self.warehouse.db.read_parquet(
                self.parquet_filepath, table_name=self.warehouse_table_name
            )

        return self.warehouse.db.table(self.warehouse_table_name)

    def get_remote_table(self) -> Expr:
        ds = InsightsDataSourcev3.get_doc(self.data_source)
        return ds.get_ibis_table(self.table_name)

    def import_remote_table(self, overwrite: bool = False):
        if os.path.exists(self.parquet_filepath) and not overwrite:
            print(
                f"Skipping creation of parquet file for {self.table_name} of {self.data_source} as it already exists."
            )
            return

        importer = WarehouseTableImporter(self)
        importer.start_import()
        t = InsightsTablev3.get_doc(
            {
                "data_source": self.data_source,
                "table": self.table_name,
            }
        )
        t.stored = 1
        t.last_synced_on = frappe.utils.now()
        t.save()


class WarehouseTableImporter:
    def __init__(self, table: WarehouseTable):
        self.table = table
        self.remote_table = None
        self.primary_key = ""
        self.warehouse_table_name = ""
        self.warehouse_folder = ""
        self.imported_batch_paths = []

        self.log = None
        self.settings = frappe._dict()

    def start_import(self):
        self.prepare_log()
        self.prepare_settings()
        self.prepare_remote_table()
        self.start_batch_import()
        self.log.ended_at = frappe.utils.now()
        self.log.time_taken = frappe.utils.time_diff_in_seconds(
            self.log.ended_at, self.log.started_at
        )
        self.log.save()

    def prepare_log(self):
        self.log = frappe.new_doc("Insights Table Import Log")
        self.log.data_source = self.table.data_source
        self.log.table_name = self.table.table_name
        self.log.started_at = frappe.utils.now()

    def prepare_settings(self) -> dict:
        self.settings.row_limit = (
            frappe.db.get_single_value("Insights Settings", "max_records_to_sync")
            or 10_00_000
        )
        self.settings.memory_limit = (
            frappe.db.get_single_value("Insights Settings", "max_memory_usage") or 512
        )
        self.log.row_limit = self.settings.row_limit
        self.log.memory_limit = self.settings.memory_limit

    def prepare_remote_table(self) -> Expr:
        self.remote_table = self.table.get_remote_table()

        if hasattr(self.remote_table, "creation"):
            self.remote_table = self.remote_table.order_by(ibis.desc("creation"))

        self.remote_table = self.remote_table.limit(self.settings.row_limit)
        self.log.query = ibis.to_sql(self.remote_table)

        if not hasattr(self.remote_table, "creation"):
            self.remote_table = self.remote_table.mutate(__row_number=ibis.row_number())

    def start_batch_import(self):
        self.primary_key = (
            "creation" if hasattr(self.remote_table, "creation") else "__row_number"
        )
        self.warehouse_table_name = self.table.warehouse_table_name
        self.warehouse_folder = get_warehouse_folder_path()
        self.imported_batch_paths = []

        try:
            batch_size = self.calculate_batch_size()
            self.process_batches(batch_size)
            self.merge_batches()
        finally:
            self._cleanup()

    def calculate_batch_size(self) -> int:
        sample_size = 10
        sample_rows = self.remote_table.head(sample_size).execute()
        total_size = sum(
            sample_rows[column].memory_usage(deep=True)
            for column in sample_rows.columns
        )
        row_size = total_size / sample_size / (1024 * 1024)
        batch_size = int(self.settings.memory_limit / row_size)
        self.log.row_size = row_size * 1024
        self.log.batch_size = batch_size
        return batch_size

    def process_batches(self, batch_size: int):
        remote_table = self.remote_table.order_by(self.primary_key)
        batch_number = 0

        while True:
            self.log.append_message(f"Processing batch: {batch_number + 1}")
            batch = remote_table.head(batch_size)
            path = self.create_parquet_file(batch, batch_number)
            self.imported_batch_paths.append(path)

            metadata = self.get_batch_metadata(path)
            if metadata["count"] < batch_size:
                break

            remote_table = remote_table.filter(
                _[self.primary_key] > metadata["max_primary_key"]
            )
            batch_number += 1

    def create_parquet_file(self, batch: Expr, batch_number: int) -> str:
        batch_file_name = f"{self.warehouse_table_name}_{batch_number}.parquet"
        path = os.path.join(self.warehouse_folder, batch_file_name)
        self.log.append_message(f"Batch Query: \n{ibis.to_sql(batch)}")
        batch.to_parquet(path, compression="snappy")
        return path

    def get_batch_metadata(self, path: str) -> dict:
        ddb = ibis.duckdb.connect(":memory:")
        batch = ddb.read_parquet(path)
        metadata = (
            batch.aggregate(
                count=_.count(),
                max_primary_key=_[self.primary_key].max(),
            )
            .execute()
            .to_records(index=False)[0]
        )
        self.log.append_message(
            f"Rows: {metadata['count']}\n" f"Bookmark: {metadata['max_primary_key']}"
        )
        ddb.disconnect()
        return metadata

    def merge_batches(self):
        ddb = ibis.duckdb.connect(":memory:")
        merged = ddb.read_parquet(
            self.imported_batch_paths, table_name=self.warehouse_table_name
        )
        path = os.path.join(
            self.warehouse_folder, f"{self.warehouse_table_name}.parquet"
        )
        if hasattr(merged, "__row_number"):
            merged = merged.drop("__row_number")
        merged.to_parquet(path, compression="snappy")

        total_rows = int(merged.count().execute())
        self.log.parquet_file = path
        self.log.rows_imported = total_rows
        self.log.append_message(
            f"Total Batches: {len(self.imported_batch_paths)}\n"
            f"Total Rows: {total_rows}"
        )
        ddb.disconnect()

    def _cleanup(self):
        for path in self.imported_batch_paths:
            if os.path.exists(path):
                os.remove(path)


def get_warehouse_folder_path() -> str:
    path = os.path.realpath(get_files_path(is_private=1))
    path = os.path.join(path, "insights_data_warehouse")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_warehouse_table_name(data_source: str, table_name: str) -> str:
    return f"{frappe.scrub(data_source)}.{frappe.scrub(table_name)}"


def get_parquet_filepath(data_source: str, table_name: str) -> str:
    warehouse_path = get_warehouse_folder_path()
    warehouse_table = get_warehouse_table_name(data_source, table_name)
    return os.path.join(warehouse_path, f"{warehouse_table}.parquet")
