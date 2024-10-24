import os

import frappe
import frappe.utils
import ibis
from frappe.utils import get_files_path
from ibis import BaseBackend, _
from ibis.expr.types import Expr

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

    def get_table(self, data_source, table_name, use_live_connection=True):
        if use_live_connection:
            return self.get_remote_table(data_source, table_name)
        else:
            return self.get_warehouse_table(data_source, table_name)

    def get_warehouse_table(self, data_source, table_name, sync=True):
        parquet_file = get_parquet_filepath(data_source, table_name)
        warehouse_table = get_warehouse_table_name(data_source, table_name)

        if not os.path.exists(parquet_file):
            if sync:
                self.import_remote_table(data_source, table_name)
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

    def import_remote_table(self, data_source, table_name, force=False):
        path = get_parquet_filepath(data_source, table_name)
        if os.path.exists(path) and not force:
            print(
                f"Skipping creation of parquet file for {table_name} of {data_source} as it already exists. "
                "Skipping insights table creation as well."
            )
            return

        max_records_to_sync = (
            frappe.db.get_single_value("Insights Settings", "max_records_to_sync")
            or 10_00_000
        )
        max_memory_usage = (
            frappe.db.get_single_value("Insights Settings", "max_memory_usage") or 512
        )
        ds = frappe.get_doc("Insights Data Source v3", data_source)
        remote_db = ds._get_ibis_backend()
        table = remote_db.table(table_name)

        if hasattr(table, "creation"):
            table = table.order_by(ibis.desc("creation")).limit(max_records_to_sync)
            table_name = get_warehouse_table_name(data_source, table_name)
            batch_import_to_parquet(table, "creation", table_name, max_memory_usage)
        else:
            table = table.limit(max_records_to_sync)
            table.to_parquet(path, compression="snappy")


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


def batch_import_to_parquet(
    table: Expr, primary_key: str, table_name: str, memory_limit: int
):
    folder = get_warehouse_folder_path()
    batch_size = calculate_batch_size(table, memory_limit)
    imported_batch_paths = process_batches(
        table, primary_key, table_name, folder, batch_size
    )
    merge_batches(imported_batch_paths, table_name, folder)
    cleanup_batch_files(imported_batch_paths)


def calculate_batch_size(table: Expr, memory_limit: int) -> int:
    sample_size = 10
    sample_rows = table.head(sample_size).execute()
    total_size = sum(
        sample_rows[column].memory_usage(deep=True) for column in sample_rows.columns
    )
    row_size = total_size / sample_size / (1024 * 1024)
    batch_size = int(memory_limit / row_size)  # in MB
    print(f"Batch size: {batch_size}")
    return batch_size


def process_batches(
    table: Expr, primary_key: str, table_name: str, folder: str, batch_size: int
):
    _table = table.order_by(primary_key)
    n = 0
    max_primary_key = None
    imported_batch_paths = []

    try:
        while True:
            batch = _table.head(batch_size)
            path = create_batch_file(batch, table_name, n, folder)
            imported_batch_paths.append(path)

            metadata = get_batch_metadata(path, primary_key)
            total_rows, max_primary_key = metadata["count"], metadata["max_primary_key"]
            print_batch_info(n, table_name, total_rows, max_primary_key)

            if total_rows < batch_size:
                break

            _table = _table.filter(_[primary_key] > max_primary_key)
            n += 1

    except BaseException as e:
        cleanup_batch_files(imported_batch_paths)
        raise e

    return imported_batch_paths


def create_batch_file(
    batch: Expr, table_name: str, batch_number: int, folder: str
) -> str:
    print(f"SQL for batch {batch_number} of {table_name}: {ibis.to_sql(batch)}")
    batch_file_name = f"{table_name}_{batch_number}.parquet"
    path = os.path.join(folder, batch_file_name)
    batch.to_parquet(path, compression="snappy")
    print(f"Created batch {batch_number} for {table_name}")
    return path


def get_batch_metadata(path: str, primary_key: str):
    ddb = ibis.duckdb.connect(":memory:")
    batch = ddb.read_parquet(path)
    metadata = (
        batch.aggregate(
            count=_.count(),
            max_primary_key=_[primary_key].max(),
        )
        .execute()
        .to_records(index=False)[0]
    )
    ddb.disconnect()
    return metadata


def print_batch_info(
    batch_number: int, table_name: str, total_rows: int, max_primary_key: str
):
    print(f"Batch {batch_number} for {table_name} has {total_rows} rows")
    print(
        f"Max primary key for batch {batch_number} of {table_name}: {max_primary_key}"
    )


def merge_batches(imported_batch_paths: list[str], table_name: str, folder: str):
    print(f"Merging {len(imported_batch_paths)} batches for {table_name}")
    path = os.path.join(folder, f"{table_name}.parquet")
    ddb = ibis.duckdb.connect(":memory:")
    merged = ddb.read_parquet(imported_batch_paths, table_name=table_name)
    merged.to_parquet(path, compression="snappy")
    print(f"Created parquet file for {table_name}")
    ddb.disconnect()


def cleanup_batch_files(imported_batch_paths: list[str]):
    for path in imported_batch_paths:
        os.remove(path)
