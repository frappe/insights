import time

import frappe
import frappe.utils
import ibis
import pandas as pd
from ibis.backends.sql.datatypes import DuckDBType

import insights
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    WAREHOUSE_DB_NAME,
    WarehouseTable,
    get_warehouse_schema_name,
)


def _ibis_to_duckdb(ibis: str):
    return DuckDBType.to_string(ibis.dtype())


class SyncCursorManager:
    def _get_table_doc_name(self, data_source: str, table_name: str) -> str:
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

        return get_table_name(data_source, table_name)

    def get_cursor(self, data_source: str, table_name: str):
        doc_name = self._get_table_doc_name(data_source, table_name)
        cursor_value = frappe.db.get_value("Insights Table v3", doc_name, "cursor")
        if not cursor_value:
            return None
        parts = cursor_value.split("|||")
        if len(parts) != 2:
            return None
        return {"last_modified": parts[0], "last_name": parts[1]}

    def update_cursor(self, data_source: str, table_name: str, last_modified: str, last_name: str):
        doc_name = self._get_table_doc_name(data_source, table_name)
        cursor_value = f"{last_modified}{'|||'}{last_name}"
        frappe.db.set_value("Insights Table v3", doc_name, "cursor", cursor_value)

    def delete_cursor(self, data_source: str, table_name: str):
        doc_name = self._get_table_doc_name(data_source, table_name)
        frappe.db.set_value("Insights Table v3", doc_name, "cursor", "")


class IncrementalImporter:

    # batch size hard coded to 1000 to avoid memory issues
    def __init__(self, table: WarehouseTable, batch_size: int = 2000):
        self.table = table
        self.doctype = (
            table.table_name.replace("tab", "", 1) if table.table_name.startswith("tab") else table.table_name
        )
        self.batch_size = batch_size
        self.schema = get_warehouse_schema_name(table.data_source)
        self.cursor_mgr = SyncCursorManager()

        self.log = None
        self.last_log_time = None

    def start_sync(self):
        from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
            db_connections,
        )

        self._sync_summary = {"upserted": 0, "deleted": 0, "batches": 0}

        with db_connections():
            self._prepare_log()
            self._run_sync_loop()
            self._finalize_log()

        summary = self._sync_summary
        insights.create_toast(
            f"Synced {frappe.bold(self.table.table_name)} — "
            f"{summary['upserted']} rows upserted",
            title="Incremental Sync Completed",
            type="success",
            duration=5,
        )

    def _prepare_log(self):
        self.log = frappe.new_doc("Insights Table Import Log")
        self.log.db_insert()
        self.log.db_set(
            {
                "data_source": self.table.data_source,
                "table_name": self.table.table_name,
                "started_at": frappe.utils.now(),
                "status": "In Progress",
                "batch_size": self.batch_size,
            },
            commit=True,
        )

        insights.create_toast(
            f"Syncing {frappe.bold(self.table.table_name)} to the data store"
            "You may not see the results till the sync is completed",
            title="Incremental Sync Started",
            duration=5,
        )

    def _run_sync_loop(self):
        cursor = self.cursor_mgr.get_cursor(self.table.data_source, self.table.table_name)
        if not cursor:
            self._log("No cursor found, Running full refresh to establish baseline")
            self.log.db_set({"status": "Skipped"}, commit=True)
            self.table.enqueue_import(sync_mode="Full Refresh")
            return

        last_modified = cursor["last_modified"]
        last_name = cursor["last_name"]

        try:
            # stage 1: fetch all batches from source
            batches = self._fetch_all_batches(last_modified, last_name)
            if not batches:
                self._log("No new rows to sync")
                self.log.db_set({"status": "Completed"}, commit=True)
                self._sync_summary = {"upserted": 0, "deleted": 0, "batches": 0}
                return

            # stage 2: write all batches to warehouse
            total_upserted = self._write_batches(batches)

            # stage 3: update cursor to last row
            last_df = batches[-1]
            last_modified, last_name = self.get_cursor(last_df)
            self.cursor_mgr.update_cursor(
                self.table.data_source, self.table.table_name, last_modified, last_name
            )

            self.log.db_set({"rows_imported": total_upserted, "status": "Completed"}, commit=True)
            self._log(f"Sync complete. {total_upserted} rows upserted in {len(batches)} batches.")
            self._update_insights_table()
            self._sync_summary = {"upserted": total_upserted, "deleted": 0, "batches": len(batches)}

        except Exception as e:
            self.log.db_set({"status": "Failed"}, commit=True)
            self._log(f"Error: {e}")
            raise

    def _fetch_all_batches(self, last_modified, last_name):
        remote = self.table.get_remote_table()
        batches = []
        while True:
            self._log(f"Fetching batch {len(batches) + 1}: cursor ({last_modified}, {last_name})")
            df = self._fetch_batch(remote, last_modified, last_name)
            if df.empty:
                break
            self._log(f"Fetched {len(df)} rows")
            batches.append(df)
            last_modified, last_name = self.get_cursor(df)
            if len(df) < self.batch_size:
                break
        return batches

    def _write_batches(self, batches: list[pd.DataFrame]):
        schema = ibis.memtable(batches[0]).schema()
        self._evolve_schema(schema)
        # close cached read-only connection so write connection can open
        if WAREHOUSE_DB_NAME in insights.db_connections:
            insights.db_connections[WAREHOUSE_DB_NAME].disconnect()
            del insights.db_connections[WAREHOUSE_DB_NAME]
        total = 0
        with insights.warehouse.get_table_writer(
            self.table.warehouse_table_name, schema,
            database=self.schema, mode="upsert", upsert_key="name", log_fn=self._log,
        ) as writer:
            for df in batches:
                writer.insert(df)
                total += len(df)
        return total

    def _fetch_batch(self, remote, last_modified: str | None, last_name: str | None):
        query = remote
        if last_modified and last_name:
            query = query.filter(
                (query.modified > last_modified)
                | ((query.modified == last_modified) & (query.name > last_name))
            )
        return query.order_by(["modified", "name"]).limit(self.batch_size).execute()

    def get_cursor(self, df: pd.DataFrame):
        last_row = df.iloc[-1]
        return str(last_row["modified"]), str(last_row["name"])

    def detect_schema_changes(self, current: dict[str, str], incoming: dict[str, str]):
        current_cols = set(current.keys())
        incoming_cols = set(incoming.keys())
        added = {col: incoming[col] for col in incoming_cols - current_cols}
        removed = current_cols - incoming_cols
        return added, removed

    def _evolve_schema(self, incoming_ibis_schema: ibis.Schema):
        incoming_schema = {col: str(dtype) for col, dtype in incoming_ibis_schema.items()}

        try:
            current_table = insights.warehouse.db.table(self.table.warehouse_table_name, database=self.schema)
            current_schema = {col: str(dtype) for col, dtype in current_table.schema().items()}
        except Exception:
            return  # Table doesn't exist yet, will be created on first upsert

        added, removed = self.detect_schema_changes(current_schema, incoming_schema)

        if not added and not removed:
            return

        with insights.warehouse.get_write_connection() as db:
            db.raw_sql(f"USE '{self.schema}'")
            for col, dtype in added.items():
                duckdb_type = _ibis_to_duckdb(dtype)
                self._log(f"Adding column: {col} ({duckdb_type})")
                db.raw_sql(
                    f'ALTER TABLE "{self.table.warehouse_table_name}" ADD COLUMN "{col}" {duckdb_type}'
                )

            for col in removed:
                self._log(f"Dropping column: {col}")
                db.raw_sql(f'ALTER TABLE "{self.table.warehouse_table_name}" DROP COLUMN "{col}"')

    def _update_insights_table(self):
        from insights.utils import InsightsTablev3

        t = InsightsTablev3.get_doc(
            {
                "data_source": self.table.data_source,
                "table": self.table.table_name,
            }
        )
        t.stored = 1
        t.last_synced_on = frappe.utils.now()
        t.save()

    def _finalize_log(self):
        ended_at = frappe.utils.now()
        self.log.db_set(
            {
                "ended_at": ended_at,
                "time_taken": frappe.utils.time_diff_in_seconds(ended_at, self.log.started_at),
            },
            commit=True,
        )

    def _log(self, message: str, commit: bool = True):
        if not self.log:
            return
        if self.last_log_time is None:
            self.last_log_time = time.monotonic()
            elapsed = 0.0
        else:
            current_time = time.monotonic()
            elapsed = current_time - self.last_log_time
            self.last_log_time = current_time

        self.log.log_output(f"[{frappe.utils.now()}] [{elapsed:.1f}s] {message}", commit=commit)


def enqueue_incremental_sync(data_source: str, table_name: str):
    job_id = f"inc_sync_{frappe.scrub(data_source)}_{frappe.scrub(table_name)}"
    frappe.enqueue(
        "insights.insights.doctype.insights_data_source_v3.incremental_sync.execute_incremental_sync",
        data_source=data_source,
        table_name=table_name,
        queue="long",
        timeout=30 * 60,
        job_id=job_id,
        deduplicate=True,
    )


def execute_incremental_sync(data_source: str, table_name: str):
    table = WarehouseTable(data_source, table_name)
    importer = IncrementalImporter(table)
    importer.start_sync()
