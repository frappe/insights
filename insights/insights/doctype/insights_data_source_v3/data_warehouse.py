import os

import frappe
import frappe.utils
import ibis
import ibis.backends
import ibis.backends.duckdb
from frappe.query_builder.functions import IfNull
from frappe.utils import get_files_path
from frappe.utils.background_jobs import is_job_enqueued
from ibis import BaseBackend, _
from ibis.expr.types import Expr

from insights import create_toast
from insights.utils import InsightsDataSourcev3, InsightsTablev3

WAREHOUSE_DB_NAME = "insights.duckdb"


class Warehouse:
    def __init__(self):
        self.warehouse_path = get_warehouse_folder_path()
        self.db_path = os.path.join(self.warehouse_path, WAREHOUSE_DB_NAME)

    @property
    def db(self) -> BaseBackend:
        return self.get_connection(read_only=True)

    def get_connection(self, read_only: bool = True) -> BaseBackend:
        if not os.path.exists(self.db_path):
            ddb = ibis.duckdb.connect(self.db_path)
            ddb.disconnect()

        # Use a different key for read-write connections
        connection_key = f"{WAREHOUSE_DB_NAME}_{'ro' if read_only else 'rw'}"
        
        if connection_key not in frappe.local.insights_db_connections:
            ddb = ibis.duckdb.connect(self.db_path, read_only=read_only)
            frappe.local.insights_db_connections[connection_key] = ddb

        return frappe.local.insights_db_connections[connection_key]

    def get_table(self, data_source: str, table_name: str) -> "WarehouseTable":
        return WarehouseTable(data_source, table_name)


class WarehouseTable:
    def __init__(self, data_source: str, table_name: str):
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

        self.warehouse = Warehouse()
        self.data_source = data_source
        self.table_name = table_name
        self.warehouse_table_name = get_warehouse_table_name(data_source, table_name)
        self.table_doc_name = get_table_name(data_source, table_name)

        self.validate()

    def validate(self):
        if not self.data_source:
            frappe.throw("Data Source is required.")
        if not self.table_name:
            frappe.throw("Table Name is required.")

    def get_ibis_table(self, import_if_not_exists: bool = True) -> Expr:
        # Check if table exists in warehouse database
        table_exists = self.warehouse_table_name in self.warehouse.db.list_tables()
        
        if not table_exists:
            if import_if_not_exists:
                self.enqueue_import()
                remote_table = self.get_remote_table()
                return self.warehouse.db.create_table(
                    self.warehouse_table_name,
                    schema=remote_table.schema(),
                    temp=True,
                    overwrite=True,
                )
            else:
                frappe.throw(
                    f"{self.table_name} of {self.data_source} is not imported to the data warehouse."
                )

        return self.warehouse.db.table(self.warehouse_table_name)

    def get_remote_table(self) -> Expr:
        ds = InsightsDataSourcev3.get_doc(self.data_source)
        return ds.get_ibis_table(self.table_name)

    def enqueue_import(self):
        importer = WarehouseTableImporter(self)
        importer.enqueue_import()


class WarehouseTableImporter:
    def __init__(self, table: WarehouseTable):
        self.table = table
        self.remote_table = None
        self.primary_key = ""
        self.warehouse_table_name = ""
        self.warehouse_db = None

        self.log = None
        self.settings = frappe._dict()

    def import_in_progress(self):
        log = frappe.qb.DocType("Insights Table Import Log")
        return frappe.db.exists(
            log,
            (
                (log.data_source == self.table.data_source)
                & (log.table_name == self.table.table_name)
                & (log.status == "In Progress")
                & (IfNull(log.ended_at, "") == "")
            ),
        )

    def enqueue_import(self):
        job_id = f"import_{frappe.scrub(self.table.data_source)}_{frappe.scrub(self.table.table_name)}"

        if is_job_enqueued(job_id) or self.import_in_progress():
            create_toast(
                f"Import for {frappe.bold(self.table.table_name)} is in progress."
                "You may not see the results till the import is completed.",
                title="Import In Progress",
                type="info",
                duration=7,
            )
            return

        frappe.enqueue(
            method="frappe.call",
            fn="insights.insights.doctype.insights_data_source_v3.data_warehouse._start_table_import",
            data_source=self.table.data_source,
            table_name=self.table.table_name,
            queue="long",
            timeout=6000,
            job_id=job_id,
        )

    def start_import(self):
        from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
            db_connections,
        )

        with db_connections():
            self.prepare_log()
            self.prepare_settings()
            self.prepare_remote_table()
            self.start_batch_import()
            self.update_log()

        create_toast(
            f"Imported {frappe.bold(self.table.table_name)} to the data store. "
            "Please refresh the query to see the updated data.",
            title="Import Completed",
            type="success",
            duration=7,
        )

    def prepare_log(self):
        self.log = frappe.new_doc("Insights Table Import Log")
        self.log.db_insert()
        self.log.db_set(
            {
                "data_source": self.table.data_source,
                "table_name": self.table.table_name,
                "started_at": frappe.utils.now(),
                "status": "In Progress",
            },
            commit=True,
        )

        create_toast(
            f"Importing {frappe.bold(self.table.table_name)} to the data store. "
            "You may not see the results till the import is completed.",
            title="Import Started",
            duration=7,
        )

    def prepare_settings(self) -> dict:
        self.settings.row_limit = (
            frappe.get_value("Insights Table v3", self.table.table_doc_name, "row_limit")
            or frappe.db.get_single_value("Insights Settings", "max_records_to_sync")
            or 10_00_000
        )
        self.settings.before_import_script = (
            frappe.get_value("Insights Table v3", self.table.table_doc_name, "before_import_script") or ""
        )
        self.settings.memory_limit = (
            frappe.db.get_single_value("Insights Settings", "max_memory_usage") or 512
        )
        self.log.db_set(
            {
                "row_limit": self.settings.row_limit,
                "memory_limit": self.settings.memory_limit,
            },
            commit=True,
        )

    def prepare_remote_table(self) -> Expr:
        self.remote_table = self.table.get_remote_table()

        if hasattr(self.remote_table, "creation"):
            self.primary_key = "creation"
            self.remote_table = self.remote_table.order_by(ibis.desc("creation"))
        elif hasattr(self.remote_table, "timestamp"):
            self.primary_key = "timestamp"
            self.remote_table = self.remote_table.order_by(ibis.desc("timestamp"))
        else:
            self.primary_key = "__row_number"
            self.remote_table = self.remote_table.mutate(__row_number=ibis.row_number())

        if self.settings.before_import_script:
            from .ibis_utils import exec_with_return

            self.remote_table = exec_with_return(
                self.settings.before_import_script, {"table": self.remote_table}
            )

        self.remote_table = self.remote_table.limit(self.settings.row_limit)
        self.log.db_set("query", ibis.to_sql(self.remote_table), commit=True)

    def start_batch_import(self):
        self.warehouse_table_name = self.table.warehouse_table_name
        self.warehouse_db = self.table.warehouse.get_connection(read_only=False)

        try:
            batch_size = self.calculate_batch_size()
            self.process_batches(batch_size)
            self.update_insights_table()
            self.log.status = "Completed"
            self.log.log_output("Import completed successfully.", commit=True)
        except Exception as e:
            self.log.status = "Failed"
            self.log.log_output(f"Error: \n{e}", commit=True)
            raise e

    def calculate_batch_size(self) -> int:
        sample_size = 10
        sample_rows = self.remote_table.head(sample_size).execute()
        total_size = sum(sample_rows[column].memory_usage(deep=True) for column in sample_rows.columns)
        row_size = total_size / sample_size / (1024 * 1024)
        batch_size = int(self.settings.memory_limit / row_size)
        self.log.db_set(
            {
                "row_size": row_size * 1024,
                "batch_size": batch_size,
            },
            commit=True,
        )
        return batch_size

    def process_batches(self, batch_size: int):
        remote_table = self.remote_table.order_by(self.primary_key)
        batch_number = 0
        total_rows = 0

        # Drop table if it exists and create new one on first batch
        if batch_number == 0 and self.warehouse_table_name in self.warehouse_db.list_tables():
            self.warehouse_db.drop_table(self.warehouse_table_name)

        while True:
            self.log.log_output(f"Processing batch: {batch_number + 1}", commit=True)
            batch = remote_table.head(batch_size)
            
            self.log.log_output(f"Batch Query: \n{ibis.to_sql(batch)}", commit=True)
            
            # Execute the batch and get the data
            batch_data = batch.execute()
            row_count = len(batch_data)
            
            if row_count == 0:
                break
            
            # Get max primary key before dropping __row_number
            max_primary_key = None
            if self.primary_key in batch_data.columns:
                max_primary_key = batch_data[self.primary_key].max()
            
            # Drop __row_number column if it exists (it was added for pagination)
            if "__row_number" in batch_data.columns:
                batch_data = batch_data.drop(columns=["__row_number"])
                
            # Insert into warehouse database
            if batch_number == 0:
                # Create table on first batch
                self.warehouse_db.create_table(
                    self.warehouse_table_name,
                    obj=batch_data,
                    overwrite=True,
                )
            else:
                # Insert subsequent batches
                self.warehouse_db.insert(self.warehouse_table_name, obj=batch_data)
            
            total_rows += row_count
            
            if max_primary_key is not None:
                self.log.log_output(
                    f"Rows: {row_count}\nBookmark: {max_primary_key}",
                    commit=True,
                )
            else:
                self.log.log_output(f"Rows: {row_count}", commit=True)
            
            if row_count < batch_size:
                break

            if max_primary_key is not None:
                remote_table = remote_table.filter(_[self.primary_key] > max_primary_key)
            
            batch_number += 1

        # Log total rows imported
        self.log.rows_imported = total_rows
        self.log.log_output(
            f"Total Batches: {batch_number + 1}\nTotal Rows: {total_rows}",
            commit=True,
        )

    def update_log(self):
        self.log.db_set(
            {
                "ended_at": frappe.utils.now(),
                "time_taken": frappe.utils.time_diff_in_seconds(self.log.ended_at, self.log.started_at),
            },
            commit=True,
        )

    def update_insights_table(self):
        t = InsightsTablev3.get_doc(
            {
                "data_source": self.table.data_source,
                "table": self.table.table_name,
            }
        )
        t.stored = 1
        t.last_synced_on = frappe.utils.now()
        t.save()


# called by background job
def _start_table_import(data_source: str, table_name: str):
    table = WarehouseTable(data_source, table_name)
    importer = WarehouseTableImporter(table)
    importer.start_import()


def get_warehouse_folder_path() -> str:
    path = os.path.realpath(get_files_path(is_private=1))
    path = os.path.join(path, "insights_data_warehouse")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_warehouse_table_name(data_source: str, table_name: str) -> str:
    return f"{frappe.scrub(data_source)}.{frappe.scrub(table_name)}"
