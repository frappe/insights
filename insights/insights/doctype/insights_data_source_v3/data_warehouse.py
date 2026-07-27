import os
import shutil
import tempfile
import time
from collections.abc import Generator, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path

import frappe
import frappe.utils
import ibis
import pandas as pd
from duckdb import CatalogException
from frappe.query_builder.functions import IfNull, Max, Min
from frappe.utils import add_days, get_datetime, get_files_path, now, now_datetime
from frappe.utils.background_jobs import is_job_enqueued
from ibis import _
from ibis.backends.duckdb import Backend as DuckDBBackend
from ibis.backends.sql.datatypes import DuckDBType
from ibis.common.exceptions import TableNotFound
from ibis.expr.types import Expr, Table

import insights
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import (
    local_duckdb_write_connection,
    local_duckdb_write_lock,
    open_local_duckdb,
)
from insights.utils import InsightsDataSourcev3, InsightsTablev3

WAREHOUSE_DB_NAME = "insights"

# A stored table unused for this long is un-stored; a table imported this
# recently is never pruned, even if nothing has queried it yet.
UNUSED_TABLE_DAYS = 30
# Cleanup holds the warehouse write lock for much longer than an import commit.
CLEANUP_LOCK_TIMEOUT = 15 * 60
# Rebuilding the file is only worth the disk and time above these thresholds.
COMPACT_MIN_FILE_SIZE = 100 * 1024 * 1024
COMPACT_MIN_FREE_RATIO = 0.2


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


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

        db = open_local_duckdb(
            path,
            read_only=read_only,
            allowed_dir=str(Path(tempfile.gettempdir())) if not read_only else None,
        )

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
        path = self.get_db_path()
        allowed_dir = str(Path(tempfile.gettempdir()))

        with local_duckdb_write_connection(
            path, cache_key=WAREHOUSE_DB_NAME, allowed_dir=allowed_dir, timeout=timeout
        ) as db:
            if database:
                db.raw_sql(f"USE '{database}'")
            yield db

    def get_table(self, data_source: str, table_name: str) -> "WarehouseTable":
        return WarehouseTable(data_source, table_name)

    def get_table_writer(
        self,
        table_name: str,
        schema: ibis.Schema,
        database: str = "main",
        mode: str = "replace",
        primary_key_column: str = "",
        cursor_column: str = "",
        log_fn=None,
    ) -> "WarehouseTableWriter":
        """Create a table writer for batch inserts with automatic cleanup.

        Usage:
            with warehouse.get_table_writer("table", schema, database="my_schema") as writer:
                writer.insert(df1)
                writer.insert(df2)
            # On successful exit, data is committed to warehouse
            # On exception, temp files are cleaned up automatically
        """
        return WarehouseTableWriter(
            table_name,
            table_schema=schema,
            database=database,
            mode=mode,
            primary_key_column=primary_key_column,
            cursor_column=cursor_column,
            log_fn=log_fn,
        )


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
        primary_key_column: str = "",
        cursor_column: str = "",
        log_fn=None,
    ):
        self.database = database
        self.table_name = table_name
        self.table_schema = table_schema
        self.mode = mode
        self.primary_key_column = primary_key_column
        self.cursor_column = cursor_column
        self._log = log_fn or (lambda *args, **kwargs: None)

        self._temp_dir: Path | None = None
        self._parquet_files: list[Path] = []
        self._committed = False
        self._batch_count = 0

    def __enter__(self) -> "WarehouseTableWriter":
        self._temp_dir = Path(tempfile.mkdtemp(prefix="insights_import_"))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
            return False

        if not self._committed:
            self.commit()

        self._cleanup_temp_dir()
        return False

    def insert(self, data: pd.DataFrame | Expr) -> Expr:
        if self._temp_dir is None:
            raise RuntimeError("WarehouseTableWriter must be used as a context manager")

        # switch to memory backend for writing to temp directory
        data = ibis.memtable(data)

        parquet_path = self._temp_dir / f"batch_{self._batch_count + 1}.parquet"
        self._log(f"Writing batch {self._batch_count + 1}")
        data.to_parquet(parquet_path)

        self._parquet_files.append(parquet_path)
        self._batch_count += 1

        return ibis.read_parquet(parquet_path)

    def commit(self) -> int:
        if self._committed:
            return 0

        if not self._parquet_files:
            self._committed = True
            self._cleanup_temp_dir()
            return 0

        total_rows = 0
        try:
            with insights.warehouse.get_write_connection() as db:
                self._log(f"Committing {len(self._parquet_files)} parquet files to '{self.table_name}'")

                with suppress(CatalogException):
                    db.create_database(self.database)

                db.raw_sql(f"USE '{self.database}'")

                self._log(f"Switched to '{self.database}' database")

                parquet_glob = str(self._temp_dir / "*.parquet")
                merged = db.read_parquet(parquet_glob)

                if self._table_exists(db) and self.mode in ("append", "upsert"):
                    self._add_missing_columns(db, merged)
                    if self.mode == "append":
                        db.insert(self.table_name, merged)
                    elif self.mode == "upsert":
                        self._upsert(db, merged)
                else:
                    db.create_table(self.table_name, merged, schema=self.table_schema, overwrite=True)

                self._log("Commit completed.")

                total_rows = merged.count().execute()
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

    def _add_missing_columns(self, db: DuckDBBackend, incoming: Table) -> None:
        """Add columns the source has gained since the last import.

        ibis inserts by name only while the source columns are a subset of the
        target's; a new source column otherwise falls back to positional order.
        """
        existing_schema = db.table(self.table_name).schema()

        for name, dtype in incoming.schema().items():
            if name in existing_schema:
                continue
            column_type = DuckDBType.to_string(dtype)
            self._log(f"New column '{name}' ({column_type}), adding it to '{self.table_name}'")
            table = quote_ident(self.table_name)
            db.raw_sql(f"ALTER TABLE {table} ADD COLUMN {quote_ident(name)} {column_type}")

    def _upsert(self, db: DuckDBBackend, incoming: Table) -> None:
        if not self.primary_key_column or not self.cursor_column:
            raise RuntimeError("Upsert mode requires both cursor and primary key columns")

        source_query = ibis.to_sql(incoming, dialect="duckdb", pretty=False)
        merge_stmt = self._build_merge_statement(source_query, incoming.schema().names)
        self._log(f"MERGE Query:\n{merge_stmt}")
        db.raw_sql(merge_stmt)

    def _build_merge_statement(self, source_query: str, columns: Sequence[str]) -> str:
        source_alias = "source"
        target_alias = "target"

        def qualified_column(name: str, table: str) -> str:
            return f"{table}.{quote_ident(name)}"

        assignments = ", ".join(
            f"{quote_ident(name)} = {qualified_column(name, source_alias)}" for name in columns
        )
        insert_columns = ", ".join(quote_ident(name) for name in columns)
        insert_values = ", ".join(qualified_column(name, source_alias) for name in columns)

        return (
            f"MERGE INTO {quote_ident(self.table_name)} AS {target_alias} "
            f"USING ({source_query}) AS {source_alias} "
            f"ON {qualified_column(self.primary_key_column, target_alias)} = "
            f"{qualified_column(self.primary_key_column, source_alias)} "
            f"WHEN MATCHED THEN UPDATE SET {assignments} "
            f"WHEN NOT MATCHED THEN INSERT ({insert_columns}) VALUES ({insert_values})"
        )

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
        self._log("Temporary files cleaned up.")

    @property
    def batch_count(self) -> int:
        """Number of batches inserted so far."""
        return self._batch_count


class WarehouseTable:
    def __init__(self, data_source: str, table_name: str):
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

        self.data_source = data_source
        self.table_name = table_name
        self.schema = get_warehouse_schema_name(data_source)
        self.warehouse_table_name = frappe.scrub(table_name)
        self.table_doc_name = get_table_name(data_source, table_name)

        self.validate()

    def validate(self):
        if not self.data_source:
            frappe.throw("Data Source is required.")
        if not self.table_name:
            frappe.throw("Table Name is required.")

    def get_ibis_table(self, import_if_not_exists: bool = True) -> Expr:
        try:
            return insights.warehouse.db.table(self.warehouse_table_name, database=self.schema)
        except TableNotFound:
            if import_if_not_exists:
                self.enqueue_import()
                remote_table = self.get_remote_table()
                return insights.warehouse.db.create_table(
                    self.warehouse_table_name,
                    schema=remote_table.schema(),
                    database=self.schema,
                    temp=True,
                    overwrite=True,
                )
            else:
                frappe.throw(
                    f"{self.table_name} of {self.data_source} is not imported to the data warehouse."
                )
        except Exception as e:
            frappe.log_error(e)
            frappe.throw("Error accessing the data warehouse. Please try again.")

    def get_remote_table(self) -> Expr:
        ds = InsightsDataSourcev3.get_doc(self.data_source)
        return ds.get_ibis_table(self.table_name)

    def enqueue_import(self):
        if frappe.db.get_value("Insights Data Source v3", self.data_source, "type") == "REST API":
            frappe.throw("Import not supported for API data sources")

        importer = WarehouseTableImporter(self)
        importer.enqueue_import()

    def drop(self) -> None:
        """Drop this table from the warehouse. No-op if it does not exist."""
        with insights.warehouse.get_write_connection(self.schema) as db:
            with suppress(Exception):
                db.drop_table(self.warehouse_table_name, force=True)


class WarehouseTableImporter:
    def __init__(self, table: WarehouseTable):
        self.table = table
        self.remote_table: Table = None
        self.remote_table_schema = None
        self.cursor_column = ""
        self.dedupe_key_column = ""
        self.warehouse_table_name = ""
        self.sync_strategy = "Append Only"
        self.writer_mode = "replace"  # overridden to "append" for incremental syncs

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
            try:
                self.prepare_settings()
                self.prepare_remote_table()
                self.start_batch_import()
            except Exception:
                if self.log.status != "Failed":
                    self.log.status = "Failed"
                    self._log(frappe.get_traceback())
                raise
            finally:
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
        table_doc = frappe.get_value(
            "Insights Table v3",
            self.table.table_doc_name,
            [
                "row_limit",
                "before_import_script",
                "sync_mode",
                "sync_strategy",
                "sync_cursor_column",
                "sync_primary_key_column",
                "sync_from",
                "last_sync_bookmark",
            ],
            as_dict=True,
        )
        self.settings.row_limit = (
            table_doc.row_limit
            or frappe.db.get_single_value("Insights Settings", "max_records_to_sync")
            or 10_00_000
        )
        self.settings.before_import_script = table_doc.before_import_script or ""
        self.settings.memory_limit = (
            frappe.db.get_single_value("Insights Settings", "max_memory_usage") or 512
        )
        self.settings.sync_mode = table_doc.sync_mode or "Full"
        self.settings.sync_strategy = table_doc.sync_strategy or "Append Only"
        self.settings.sync_cursor_column = table_doc.sync_cursor_column or ""
        self.settings.sync_primary_key_column = table_doc.sync_primary_key_column or ""
        self.settings.sync_from = table_doc.sync_from  # Datetime or None
        self.settings.last_sync_bookmark = table_doc.last_sync_bookmark or ""
        self.log.db_set(
            {
                "row_limit": self.settings.row_limit,
                "memory_limit": self.settings.memory_limit,
            },
            commit=True,
        )
        self._log(
            f"Settings: sync_mode={self.settings.sync_mode}"
            f", strategy={self.settings.sync_strategy}"
            f", cursor={self.settings.sync_cursor_column or 'N/A'}"
            f", key={self.settings.sync_primary_key_column or 'N/A'}"
            f", sync_from={self.settings.sync_from or 'N/A'}"
            f", bookmark={self.settings.last_sync_bookmark or 'N/A'}"
            f", row_limit={self.settings.row_limit}"
        )

    def _disable_statement_timeout(self):
        """Disable statement timeout on the remote connection.

        Import jobs are long-running background tasks managed by the queue
        worker, so the user-facing max_execution_time limit should not apply.
        """
        backend = insights.db_connections.get(self.table.data_source)
        if backend is None:
            return
        with suppress(Exception):
            backend.raw_sql("SET MAX_STATEMENT_TIME=0")

    def prepare_remote_table(self) -> Expr:
        self.remote_table = self.table.get_remote_table()
        self._disable_statement_timeout()

        if self.settings.sync_mode == "Incremental":
            self._prepare_incremental_table()
        else:
            self._prepare_full_table()

        self.remote_table_schema = self.remote_table.schema()
        self.log.db_set("query", ibis.to_sql(self.remote_table), commit=True)

    def _apply_before_import_script(self) -> None:
        if self.settings.before_import_script:
            from .ibis_utils import exec_with_return

            self.remote_table = exec_with_return(
                self.settings.before_import_script, {"table": self.remote_table}
            )

    def _prepare_full_table(self) -> None:
        if hasattr(self.remote_table, "creation"):
            self.cursor_column = "creation"
        elif hasattr(self.remote_table, "timestamp"):
            self.cursor_column = "timestamp"
        else:
            self.cursor_column = ""

        self.dedupe_key_column = ""

        self._apply_before_import_script()
        self.remote_table = self.apply_limit(self.remote_table)
        self.writer_mode = "replace"

    def _prepare_incremental_table(self) -> None:
        self.cursor_column = self.settings.sync_cursor_column
        self.dedupe_key_column = self.settings.sync_primary_key_column
        self.sync_strategy = self.settings.sync_strategy or "Append Only"

        self._apply_before_import_script()

        bookmark = self._resolve_incremental_bookmark()
        self._log(f"Incremental sync: {self.cursor_column} > {bookmark}")
        self.remote_table = self.remote_table.filter(_[self.cursor_column] > bookmark)

        self.writer_mode = "upsert" if self.sync_strategy == "Update or Insert" else "append"

    def _resolve_incremental_bookmark(self):
        """Return the cursor value to filter from for incremental sync, following this precedence:
        1. Last sync bookmark (if exists and valid)
        2. Sync From date (if set)
        3. Throw error if neither is available
        """
        bookmark = self.settings.last_sync_bookmark

        if bookmark:
            # Verify the warehouse table still exists; if not, treat as first sync
            try:
                insights.warehouse.db.table(self.table.warehouse_table_name, database=self.table.schema)
            except TableNotFound:
                self._log("Warehouse table not found despite existing bookmark — falling back to sync_from.")
                bookmark = ""

        if bookmark:
            return bookmark

        if self.settings.sync_from:
            return str(self.settings.sync_from)

        frappe.throw(
            f"Incremental sync for <b>{self.table.table_name}</b> has no bookmark and no Sync From date. "
            "Set a <b>Sync From</b> date on the table to define where the first import should start."
        )

    def apply_limit(self, table: Expr) -> Expr:
        if not self.cursor_column:
            return table.limit(self.settings.row_limit)

        pk = self.cursor_column
        cutoff_row = (
            table.order_by(ibis.desc(pk, nulls_first=False))
            # OFFSET to the Nth row
            # Only selects the pk column so the query is a covering index scan
            .limit(1, offset=self.settings.row_limit - 1)
            .select(pk)
            .execute()
        )

        if len(cutoff_row) == 0:
            return table

        cutoff_value = cutoff_row[pk].iloc[0]
        self._log(f"Row limit cutoff: {pk} >= {cutoff_value}")

        # replace LIMIT with WHERE clause
        return table.filter(_[pk] >= cutoff_value)

    def start_batch_import(self):
        self.warehouse_table_name = self.table.warehouse_table_name

        try:
            batch_size = self.calculate_batch_size()
            with insights.warehouse.get_table_writer(
                self.warehouse_table_name,
                self.remote_table_schema,
                database=self.table.schema,
                mode=self.writer_mode,
                primary_key_column=self.dedupe_key_column,
                cursor_column=self.cursor_column,
                log_fn=self._log,
            ) as writer:
                total_rows = self.process_batches(batch_size, writer)
                self.log.rows_imported = total_rows
            self.update_insights_table()
            self.log.status = "Completed"
            self._log("Import completed successfully.")
        except Exception as e:
            self.log.status = "Failed"
            self._log(f"Error:\n{frappe.get_traceback()}")
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
        remote_table = self.remote_table
        if self.cursor_column:
            remote_table = remote_table.order_by(
                ibis.asc(self.cursor_column, nulls_first=True),
            )

        batch_number = 0
        total_rows = 0

        while True:
            self._log(f"Processing batch: {batch_number + 1}")
            batch = remote_table.head(batch_size)
            self._log(f"Batch Query: \n{ibis.to_sql(batch)}")

            batch = writer.insert(batch)

            batch_count = int(batch.count().execute())
            total_rows += batch_count

            self._log(f"Rows: {batch_count} Total Rows: {total_rows}")

            if batch_count < batch_size or not self.cursor_column:
                break

            last_cursor = batch[self.cursor_column].max().execute()
            self._log(f"Bookmark: {last_cursor}")
            remote_table = remote_table.filter(_[self.cursor_column] > last_cursor)
            batch_number += 1

        self._log(f"Total Batches: {batch_number + 1} Total Rows: {total_rows}")
        return total_rows

    def update_log(self):
        ended_at = frappe.utils.now()
        self.log.db_set(
            {
                "ended_at": ended_at,
                "time_taken": frappe.utils.time_diff_in_seconds(ended_at, self.log.started_at),
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

        if self.settings.sync_mode == "Incremental" and self.cursor_column:
            new_bookmark = self._read_warehouse_bookmark()
            if new_bookmark is not None:
                t.last_sync_bookmark = str(new_bookmark)
            self._log(f"Bookmark updated: {self.cursor_column} = {new_bookmark}")

        t.save(ignore_permissions=True)

    def _read_warehouse_bookmark(self):
        """Query DuckDB for the MAX cursor value after a successful incremental import.

        Reading from the warehouse (not the remote query) ensures the bookmark
        matches what was actually committed, surviving partial failures.
        """
        try:
            wh_table = insights.warehouse.db.table(
                self.table.warehouse_table_name, database=self.table.schema
            )
            return wh_table[self.cursor_column].max().execute()
        except Exception:
            self._log("Warning: could not read bookmark from warehouse table.")
            return None

    def _log(self, message: str, commit: bool = True):
        if self.last_log_time is None:
            self.last_log_time = time.monotonic()
            elapsed = 0.0
        else:
            current_time = time.monotonic()
            elapsed = current_time - self.last_log_time
            self.last_log_time = current_time

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
    )


def execute_warehouse_table_import(data_source: str, table_name: str):
    table = WarehouseTable(data_source, table_name)
    importer = WarehouseTableImporter(table)
    importer.start_import()


def get_warehouse_schema_name(data_source: str) -> str:
    """Return the DuckDB schema name for a given data source name."""
    return frappe.scrub(data_source).replace(".", "_")


def cleanup_data_store():
    """Weekly: un-store unused tables, drop orphans from DuckDB, compact the file.

    Pruning is reversible by design — `get_ibis_table(import_if_not_exists=True)`
    re-imports a dropped table the next time a query needs it.
    """
    logger = frappe.logger()
    cutoff = add_days(now_datetime(), -UNUSED_TABLE_DAYS)

    pruned = prune_unused_tables(cutoff)
    # DuckDB work is not part of this transaction: commit the docs first so a
    # later failure leaves an orphan for next week, not a `stored` table whose
    # warehouse table has already been dropped.
    frappe.db.commit()  # nosemgrep

    orphans = drop_orphan_warehouse_tables()
    compacted = compact_warehouse()

    summary = {
        "tables_pruned": len(pruned),
        "orphans_dropped": len(orphans),
        "size_before": compacted[0] if compacted else None,
        "size_after": compacted[1] if compacted else None,
    }
    logger.info(f"Data store cleanup: {summary}")
    return summary


def prune_unused_tables(cutoff) -> list[str]:
    """Flip `stored` off for tables no query has read since `cutoff`.

    Incremental tables are never pruned: re-importing them restarts from
    `sync_from` and history the source has purged since is unrecoverable.
    """
    logger = frappe.logger()

    oldest_execution = frappe.db.get_value(
        "Insights Query Execution Log", {}, "creation", order_by="creation asc"
    )
    if not oldest_execution or get_datetime(oldest_execution) > cutoff:
        # New site, or the log was trimmed via Log Settings. Every table would
        # look unused — skip rather than prune everything at once.
        logger.info("Data store cleanup: execution log is shorter than the unused window, skipping prune")
        return []

    candidates = frappe.get_all(
        "Insights Table v3",
        filters={"stored": 1},
        fields=["name", "data_source", "table", "sync_mode"],
    )
    candidates = [t for t in candidates if t.sync_mode != "Incremental"]
    if not candidates:
        return []

    last_used = get_last_execution_per_table()
    first_imported = get_first_import_per_table()

    pruned = []
    for table in candidates:
        key = (table.data_source, table.table)

        used_on = last_used.get(key)
        if used_on and used_on > cutoff:
            continue

        imported_on = first_imported.get(key)
        if imported_on and imported_on > cutoff:
            # Stored recently but not queried yet — give it time to be used.
            continue

        frappe.db.set_value(
            "Insights Table v3",
            table.name,
            {"stored": 0, "last_synced_on": None, "last_sync_bookmark": None},
            update_modified=False,
        )
        pruned.append(table.name)

        reason = f"last execution {(now_datetime() - used_on).days}d ago" if used_on else "never executed"
        logger.info(f"Data store cleanup: pruned '{table.name}' ({reason})")

    return pruned


def get_last_execution_per_table() -> dict[tuple[str, str], object]:
    """Map (data_source, table) to when a query last read it.

    A query execution counts as usage of every table its dependency chain
    reads, not just the tables it names directly — nested queries are not
    logged separately.
    """
    ExecutionLog = frappe.qb.DocType("Insights Query Execution Log")
    executions = (
        frappe.qb.from_(ExecutionLog)
        .select(ExecutionLog.query, Max(ExecutionLog.creation).as_("last_executed_on"))
        .groupby(ExecutionLog.query)
        .run(as_dict=True)
    )
    executions = {r.query: get_datetime(r.last_executed_on) for r in executions if r.query}
    if not executions:
        return {}

    references = frappe.get_all(
        "Insights Query Reference",
        fields=["query", "ref_type", "data_source", "table_name", "ref_query"],
    )
    query_deps: dict[str, list[str]] = {}
    table_deps: dict[str, list[tuple[str, str]]] = {}
    for ref in references:
        if ref.ref_type == "Query" and ref.ref_query:
            query_deps.setdefault(ref.query, []).append(ref.ref_query)
        elif ref.ref_type == "Table" and ref.table_name:
            table_deps.setdefault(ref.query, []).append((ref.data_source, ref.table_name))

    last_used: dict[tuple[str, str], object] = {}
    for query, executed_on in executions.items():
        visited = set()
        stack = [query]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            for key in table_deps.get(node, []):
                if key not in last_used or last_used[key] < executed_on:
                    last_used[key] = executed_on
            stack.extend(query_deps.get(node, []))

    return last_used


def get_first_import_per_table() -> dict[tuple[str, str], object]:
    ImportLog = frappe.qb.DocType("Insights Table Import Log")
    imports = (
        frappe.qb.from_(ImportLog)
        .select(
            ImportLog.data_source,
            ImportLog.table_name,
            Min(ImportLog.creation).as_("first_imported_on"),
        )
        .where(ImportLog.status == "Completed")
        .groupby(ImportLog.data_source, ImportLog.table_name)
        .run(as_dict=True)
    )
    return {(r.data_source, r.table_name): get_datetime(r.first_imported_on) for r in imports}


def drop_orphan_warehouse_tables() -> list[str]:
    """Drop warehouse tables that no longer have a `stored` doc behind them.

    Covers deleted data sources (their whole schema), deleted table docs,
    tables just pruned, and legacy flat `source.table` tables left in `main`.
    An orphan has no doc left to hold a bookmark or sync config, so the
    "never touch incremental" rule does not apply to it.
    """
    logger = frappe.logger()

    expected = {
        (get_warehouse_schema_name(t.data_source), frappe.scrub(t.table))
        for t in frappe.get_all("Insights Table v3", filters={"stored": 1}, fields=["data_source", "table"])
    }

    dropped = []
    with insights.warehouse.get_write_connection(timeout=CLEANUP_LOCK_TIMEOUT) as db:
        tables = db.raw_sql(
            "select schema_name, table_name from duckdb_tables() where database_name = current_database()"
        ).fetchall()

        for schema, table in tables:
            if (schema, table) in expected:
                continue
            db.raw_sql(f"DROP TABLE IF EXISTS {quote_identifier(schema)}.{quote_identifier(table)}")
            dropped.append(f"{schema}.{table}")
            logger.info(f"Data store cleanup: dropped '{schema}.{table}' (orphan: no matching doc)")

        occupied = {schema for schema, table in tables if (schema, table) in expected}
        schemas = db.raw_sql(
            "select schema_name from duckdb_schemas() "
            "where database_name = current_database() and not internal"
        ).fetchall()
        for (schema,) in schemas:
            if schema == "main" or schema in occupied:
                continue
            # Anything else still in the schema (a view, a sequence) keeps it.
            with suppress(Exception):
                db.raw_sql(f"DROP SCHEMA IF EXISTS {quote_identifier(schema)}")
                logger.info(f"Data store cleanup: dropped empty schema '{schema}'")

    return dropped


def compact_warehouse() -> tuple[int, int] | None:
    """Rebuild the warehouse file to reclaim disk, if it is worth doing.

    `DROP TABLE` reuses freed blocks but never shrinks the file, so the only
    way down from the high-water mark is copying the live data into a fresh
    file and swapping it in. Returns (size before, size after), or None when
    the rebuild was skipped or failed.
    """
    logger = frappe.logger()

    path = insights.warehouse.get_db_path()
    if not os.path.exists(path):
        return None

    size_before = os.path.getsize(path)
    if size_before < COMPACT_MIN_FILE_SIZE:
        return None

    folder = os.path.dirname(path)
    new_path = f"{path}.compact"

    with local_duckdb_write_lock(path, cache_key=WAREHOUSE_DB_NAME, timeout=CLEANUP_LOCK_TIMEOUT):
        # ATTACH-ing the new file needs the warehouse folder allowed, not tmp.
        db = open_local_duckdb(path, read_only=False, allowed_dir=folder)
        try:
            if get_free_block_ratio(db) < COMPACT_MIN_FREE_RATIO:
                return None
            copy_database_to(db, new_path)
        except Exception:
            logger.exception("Data store cleanup: failed to compact the warehouse, keeping the old file")
            with suppress(OSError):
                os.remove(new_path)
            return None
        finally:
            db.disconnect()

        # Still under the lock: no one can open the old file mid-swap.
        with suppress(OSError):
            os.remove(f"{path}.wal")
        os.rename(new_path, path)

    size_after = os.path.getsize(path)
    logger.info(f"Data store cleanup: compacted warehouse {size_before} → {size_after} bytes")
    return size_before, size_after


def copy_database_to(db: DuckDBBackend, new_path: str) -> None:
    with suppress(OSError):
        os.remove(new_path)

    database = db.raw_sql("select current_database()").fetchone()[0]
    db.raw_sql(f"ATTACH '{escape_sql_string(new_path)}' AS compacted")
    try:
        db.raw_sql(f"COPY FROM DATABASE {quote_identifier(database)} TO compacted")
    finally:
        db.raw_sql("DETACH compacted")


def get_free_block_ratio(db: DuckDBBackend) -> float:
    # Free block accounting only reflects earlier drops after a checkpoint.
    db.raw_sql("CHECKPOINT")
    total_blocks, free_blocks = db.raw_sql(
        "select total_blocks, free_blocks from pragma_database_size() "
        "where database_name = current_database()"
    ).fetchone()
    return free_blocks / total_blocks if total_blocks else 0.0


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def escape_sql_string(value: str) -> str:
    return value.replace("'", "''")


def is_warehouse(backend: DuckDBBackend):
    args = getattr(backend, "_con_args", None)
    if args and isinstance(args, tuple) and len(args) > 0:
        warehouse_db_path = insights.warehouse.get_db_path()
        return args[0] == warehouse_db_path
    return False
