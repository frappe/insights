import os
import shutil
import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from pathlib import Path

import frappe
import frappe.utils
import ibis
import pandas as pd
from duckdb import CatalogException
from frappe.query_builder.functions import IfNull
from frappe.utils import get_files_path, now
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

    def get_connection(self, database: str | None = None, read_only: bool = True) -> DuckDBBackend:
        path = self.get_db_path()

        if not os.path.exists(path):
            db = ibis.duckdb.connect(path)
            db.disconnect()

        db = ibis.duckdb.connect(path, read_only=read_only)

        if database:
            db.raw_sql(f"USE '{database}'")

        return db

    def create_database(self, database: str):
        with self.get_write_connection() as db:
            with suppress(CatalogException):
                db.create_database(database)

    @property
    def db(self) -> DuckDBBackend:
        if WAREHOUSE_DB_NAME not in insights.db_connections:
            ddb = self.get_connection(read_only=True)
            insights.db_connections[WAREHOUSE_DB_NAME] = ddb

        return insights.db_connections[WAREHOUSE_DB_NAME]

    @contextmanager
    def get_write_connection(
        self, database: str | None = None, timeout: int = 30
    ) -> Generator[DuckDBBackend, None, None]:
        from frappe.utils.synchronization import filelock

        with filelock("insights_warehouse_write", timeout=timeout):
            db = self.get_connection(database, read_only=False)
            try:
                yield db
            finally:
                db.disconnect()

    def get_table(self, data_source: str, table_name: str) -> "WarehouseTable":
        return WarehouseTable(data_source, table_name)

    def get_table_writer(
        self, table_name: str, schema: ibis.Schema, mode: str = "replace", log_fn=None
    ) -> "WarehouseTableWriter":
        """Create a table writer for batch inserts with automatic cleanup.

        Usage:
            with warehouse.get_table_writer("table", schema) as writer:
                writer.insert(df1)
                writer.insert(df2)
            # On successful exit, data is committed to warehouse
            # On exception, temp files are cleaned up automatically
        """
        return WarehouseTableWriter(table_name, table_schema=schema, mode=mode, log_fn=log_fn)


class WarehouseTableWriter:
    """Handles batch inserts to warehouse tables using temporary parquet files.

    This class abstracts the complexity of batch imports by:
    - Writing each batch to a temporary parquet file
    - On commit, reading all parquet files and inserting into DuckDB
    - On rollback/failure, cleaning up all temporary files

    The writer only acquires a write connection during the final commit phase,
    minimizing lock contention for long-running imports.
    """

    def __init__(
        self,
        table_name: str,
        table_schema: ibis.Schema,
        database: str = "main",
        mode: str = "replace",
        log_fn=None,
    ):
        self.database = database
        self.table_name = table_name
        self.table_schema = table_schema
        self.mode = mode  # 'replace' or 'append'
        self._log = log_fn or (lambda *args, **kwargs: None)

        self._temp_dir: Path | None = None
        self._parquet_files: list[Path] = []
        self._committed = False
        self._batch_count = 0

    def __enter__(self) -> "WarehouseTableWriter":
        self._temp_dir = Path(tempfile.mkdtemp(prefix="insights_import_"))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and not self._committed:
            # Normal exit without explicit commit - auto commit
            self.commit()
        else:
            # Exception occurred or already committed - cleanup
            self.rollback()
        return False

    def insert(self, data: pd.DataFrame) -> None:
        if self._temp_dir is None:
            raise RuntimeError("WarehouseTableWriter must be used as a context manager")

        if len(data) == 0:
            return

        parquet_path = self._temp_dir / f"batch_{self._batch_count + 1}.parquet"
        self._log(f"Writing batch {self._batch_count + 1}")
        ibis.memtable(data, schema=self.table_schema).to_parquet(parquet_path)
        self._log(f"Wrote {len(data)} rows")
        self._parquet_files.append(parquet_path)
        self._batch_count += 1

    def commit(self) -> int:
        if self._committed:
            return 0

        if not self._parquet_files:
            self._committed = True
            self._cleanup_temp_dir()
            return 0

        total_rows = 0
        try:
            with insights.warehouse.get_write_connection(self.database) as db:
                parquet_glob = str(self._temp_dir / "*.parquet")
                self._log(f"Committing {len(self._parquet_files)} parquet files to '{self.table_name}'")

                table_exists = self._table_exists(db)

                if self.mode == "append" and table_exists:
                    p = db.read_parquet(parquet_glob, table_name=self.table_name)
                    db.insert(self.table_name, p)
                else:
                    p = db.read_parquet(parquet_glob, table_name=self.table_name)
                    db.create_table(self.table_name, p, schema=self.table_schema, overwrite=True)

                self._log("Commit completed.")

                total_rows = db.raw_sql(f"SELECT COUNT(*) FROM read_parquet('{parquet_glob}')").fetchone()[0]
                total_rows = int(total_rows)

            self._committed = True
        finally:
            self._cleanup_temp_dir()

        return total_rows

    def _table_exists(self, db: DuckDBBackend) -> bool:
        try:
            return db.list_tables(like=f"^{self.table_name}$")
        except Exception:
            return False

    def rollback(self) -> None:
        """Rollback and cleanup all temporary files."""
        self._log("Rolling back and cleaning up temporary files")
        self._cleanup_temp_dir()

    def _cleanup_temp_dir(self) -> None:
        """Remove the temporary directory and all parquet files."""
        if self._temp_dir and self._temp_dir.exists():
            with suppress(Exception):
                shutil.rmtree(self._temp_dir)
        self._temp_dir = None
        self._parquet_files = []

    @property
    def batch_count(self) -> int:
        """Number of batches inserted so far."""
        return self._batch_count


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
        self.last_log_time = None
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
        if self.primary_key != "__row_number":
            self.remote_table_schema = self.remote_table.schema()
        else:
            self.remote_table_schema = self.remote_table.drop("__row_number").schema()

        self.log.db_set("query", ibis.to_sql(self.remote_table), commit=True)

    def start_batch_import(self):
        self.warehouse_table_name = self.table.warehouse_table_name

        try:
            batch_size = self.calculate_batch_size()
            with insights.warehouse.get_table_writer(
                self.warehouse_table_name, self.remote_table_schema, log_fn=self._log
            ) as writer:
                total_rows = self.process_batches(batch_size, writer)
                self.log.rows_imported = total_rows
            self.update_insights_table()
            self.log.status = "Completed"
            self._log("Import completed successfully.", commit=True)
        except Exception as e:
            self.log.status = "Failed"
            self._log(f"Error: \n{e}", commit=True)
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

    def process_batches(self, batch_size: int, writer: WarehouseTableWriter) -> int:
        remote_table = self.remote_table.order_by(self.primary_key)
        batch_number = 0
        total_rows = 0

        while True:
            self._log(f"Processing batch: {batch_number + 1}", commit=True)
            batch = remote_table.head(batch_size)
            self._log(f"Batch Query: \n{ibis.to_sql(batch)}", commit=True)

            batch_df = batch.execute()
            batch_count = len(batch_df)
            total_rows += batch_count

            df = batch_df
            if self.primary_key == "__row_number":
                df = batch_df.drop(columns="__row_number")
            writer.insert(df)

            self._log(
                f"Rows: {batch_count} Total Rows: {total_rows}",
                commit=True,
            )

            if batch_count < batch_size:
                break

            max_primary_key = batch_df[self.primary_key].max()
            self._log(f"Bookmark: {max_primary_key}", commit=True)
            remote_table = remote_table.filter(_[self.primary_key] > max_primary_key)
            batch_number += 1

        self._log(
            f"Total Batches: {batch_number + 1} Total Rows: {total_rows}",
            commit=True,
        )
        return total_rows

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

    def _log(self, message: str, commit: bool = True):
        if self.last_log_time is None:
            self.last_log_time = time.monotonic()
            elapsed = 0.0
        else:
            current_time = time.monotonic()
            elapsed = current_time - self.last_log_time
            self.last_log_time = current_time

        print(f"[{now()}] [{elapsed:.1f}s] {message}")
        self.log.log_output(f"[{now()}] [{elapsed:.1f}s] {message}", commit=commit)


def enqueue_warehouse_table_import(data_source: str, table_name: str):
    job_id = f"import_{frappe.scrub(data_source)}_{frappe.scrub(table_name)}"
    frappe.enqueue(
        "insights.insights.doctype.insights_data_source_v3.data_warehouse.execute_warehouse_table_import",
        data_source=data_source,
        table_name=table_name,
        queue="long",
        timeout=30 * 60,
        job_id=job_id,
        deduplicate=True,
        now=True,
    )


def execute_warehouse_table_import(data_source: str, table_name: str):
    table = WarehouseTable(data_source, table_name)
    importer = WarehouseTableImporter(table)
    importer.start_import()
