import os
from collections.abc import Generator
from contextlib import contextmanager, suppress

import frappe
import frappe.utils
import ibis
from duckdb import CatalogException
from frappe.query_builder.functions import IfNull
from frappe.utils import get_files_path
from frappe.utils.background_jobs import is_job_enqueued
from ibis import _
from ibis.backends.duckdb import Backend as DuckDBBackend
from ibis.expr.types import Expr

import insights
from insights.utils import InsightsDataSourcev3, InsightsTablev3

WAREHOUSE_DB_NAME = "insights"


class Warehouse:
    def __init__(self):
        pass

    def get_db_path(self) -> str:
        folder_path = os.path.realpath(get_files_path(is_private=1))
        folder_path = os.path.join(folder_path, "insights_data_warehouse")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return os.path.join(os.path.realpath(folder_path), f"{WAREHOUSE_DB_NAME}.duckdb")

    def get_connection(self, schema: str | None = None, read_only: bool = True) -> DuckDBBackend:
        path = self.get_db_path()

        if not os.path.exists(path):
            db = ibis.duckdb.connect(path)
            db.disconnect()

        db = ibis.duckdb.connect(path, read_only=read_only)

        if schema:
            db.raw_sql(f"USE '{schema}'")

        return db

    def create_schema(self, schema: str):
        with self.get_write_connection() as db:
            with suppress(CatalogException):
                db.create_database(schema)

    @property
    def db(self) -> DuckDBBackend:
        if WAREHOUSE_DB_NAME not in insights.db_connections:
            ddb = self.get_connection(read_only=True)
            insights.db_connections[WAREHOUSE_DB_NAME] = ddb

        return insights.db_connections[WAREHOUSE_DB_NAME]

    @contextmanager
    def get_write_connection(
        self, schema: str | None = None, timeout: int = 30
    ) -> Generator[DuckDBBackend, None, None]:
        from frappe.utils.synchronization import filelock

        with filelock("insights_warehouse_write", timeout=timeout):
            db = self.get_connection(schema=schema, read_only=False)
            try:
                yield db
            finally:
                with suppress(Exception):
                    db.disconnect()

    def get_table(self, data_source: str, table_name: str) -> "WarehouseTable":
        return WarehouseTable(data_source, table_name)


class WarehouseTable:
    def __init__(self, data_source: str, table_name: str):
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

        self.data_source = data_source
        self.table_name = table_name
        self.warehouse_table_name = self.format_table_name(data_source, table_name)
        self.table_doc_name = get_table_name(data_source, table_name)

        self.validate()

    @staticmethod
    def format_table_name(data_source: str, table_name: str) -> str:
        """Format a warehouse table name from data source and table name."""
        return f"{frappe.scrub(data_source)}.{frappe.scrub(table_name)}"

    def validate(self):
        if not self.data_source:
            frappe.throw("Data Source is required.")
        if not self.table_name:
            frappe.throw("Table Name is required.")

    def get_ibis_table(self, import_if_not_exists: bool = True) -> Expr:
        try:
            return insights.warehouse.db.table(self.warehouse_table_name)
        except Exception:
            if import_if_not_exists:
                self.enqueue_import()
                remote_table = self.get_remote_table()
                return insights.warehouse.db.create_table(
                    self.warehouse_table_name,
                    schema=remote_table.schema(),
                    temp=True,
                    overwrite=True,
                )
            else:
                frappe.throw(
                    f"{self.table_name} of {self.data_source} is not imported to the data warehouse."
                )

    def get_remote_table(self) -> Expr:
        ds = InsightsDataSourcev3.get_doc(self.data_source)
        return ds.get_ibis_table(self.table_name)

    def enqueue_import(self):
        if frappe.db.get_value("Insights Data Source v3", self.data_source, "type") == "REST API":
            frappe.throw("Import not supported for API data sources")

        importer = WarehouseTableImporter(self)
        importer.enqueue_import()


class WarehouseTableImporter:
    def __init__(self, table: WarehouseTable):
        self.table = table
        self.remote_table = None
        self.remote_table_schema = None
        self.primary_key = ""
        self.warehouse_table_name = ""

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
            insights.create_toast(
                f"Import for {frappe.bold(self.table.table_name)} is in progress."
                "You may not see the results till the import is completed.",
                title="Import In Progress",
                type="info",
                duration=7,
            )
            return

        enqueue_warehouse_table_import(
            data_source=self.table.data_source,
            table_name=self.table.table_name,
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

        insights.create_toast(
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

        insights.create_toast(
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
        self.remote_table_schema = self.remote_table.schema()
        self.log.db_set("query", ibis.to_sql(self.remote_table), commit=True)

    def start_batch_import(self):
        self.warehouse_table_name = self.table.warehouse_table_name

        try:
            batch_size = self.calculate_batch_size()
            with insights.warehouse.get_write_connection() as db:
                db.raw_sql("BEGIN TRANSACTION")
                try:
                    self.process_batches(batch_size, db)
                    db.raw_sql("COMMIT")
                except Exception:
                    db.raw_sql("ROLLBACK")
                    raise
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

    def process_batches(self, batch_size: int, db: DuckDBBackend):
        remote_table = self.remote_table.order_by(self.primary_key)
        batch_number = 0
        total_rows = 0

        while True:
            self.log.log_output(f"Processing batch: {batch_number + 1}", commit=True)
            batch = remote_table.head(batch_size)
            self.log.log_output(f"Batch Query: \n{ibis.to_sql(batch)}", commit=True)

            batch_df = batch.execute()
            batch_count = len(batch_df)
            total_rows += batch_count

            if batch_number == 0:
                # Create table with first batch using explicit schema
                db.create_table(
                    self.warehouse_table_name, batch_df, schema=self.remote_table_schema, overwrite=True
                )
            else:
                # Insert subsequent batches
                db.insert(self.warehouse_table_name, batch_df)

            self.log.log_output(
                f"Rows: {batch_count}\nTotal Rows: {total_rows}",
                commit=True,
            )

            if batch_count < batch_size:
                break

            max_primary_key = batch_df[self.primary_key].max()
            self.log.log_output(f"Bookmark: {max_primary_key}", commit=True)
            remote_table = remote_table.filter(_[self.primary_key] > max_primary_key)
            batch_number += 1

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


def enqueue_warehouse_table_import(data_source: str, table_name: str):
    job_id = f"import_{frappe.scrub(data_source)}_{frappe.scrub(table_name)}"
    frappe.enqueue(
        "insights.insights.doctype.insights_data_source_v3.data_warehouse.execute_warehouse_table_import",
        data_source=data_source,
        table_name=table_name,
        queue="long",
        timeout=30 * 60,
        job_id=job_id,
    )


def execute_warehouse_table_import(data_source: str, table_name: str):
    table = WarehouseTable(data_source, table_name)
    importer = WarehouseTableImporter(table)
    importer.start_import()
