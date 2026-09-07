import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from unittest.mock import patch

import frappe
import ibis
import pandas as pd
from duckdb import IOException

import insights
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import open_local_duckdb
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    WarehouseTable,
    WarehouseTableWriter,
)
from insights.tests.base import InsightsIntegrationTestCase

# A reader in this process shares the DuckDB instance, so it never conflicts.
# Only a second process reproduces the lock the web workers take in production.
HOLD_READ_LOCK = """
import sys, time, duckdb
con = duckdb.connect(sys.argv[1], read_only=True)
print("held", flush=True)
time.sleep(float(sys.argv[2]))
con.close()
"""


class TestWarehouse(InsightsIntegrationTestCase):
    def make_schema(self):
        return ibis.schema({"id": "int64", "value": "string", "modified": "timestamp"})

    def make_frame(self, rows):
        frame = pd.DataFrame(rows)
        frame["modified"] = pd.to_datetime(frame["modified"])
        return frame

    @contextmanager
    def warehouse_db(self):
        with tempfile.TemporaryDirectory(prefix="insights_warehouse_test_") as tmpdir:
            db = open_local_duckdb(
                str(Path(tmpdir) / "warehouse.duckdb"),
                read_only=False,
                allowed_dir=str(Path(tempfile.gettempdir())),
            )
            try:
                yield db
            finally:
                with suppress(Exception):
                    db.disconnect()

    @contextmanager
    def patched_warehouse(self):
        with self.warehouse_db() as db:
            with patch.object(
                insights.warehouse,
                "get_write_connection",
                self._patched_write_connection(db),
            ):
                yield db

    def _patched_write_connection(self, db):
        @contextmanager
        def get_write_connection(database=None, timeout=30):
            if database:
                db.raw_sql(f"USE '{database}'")
            yield db

        return get_write_connection

    def write_to_table(self, db, table_name, rows, mode="replace", **kwargs):
        with WarehouseTableWriter(
            table_name,
            table_schema=self.make_schema(),
            database="main",
            mode=mode,
            **kwargs,
        ) as writer:
            writer.insert(self.make_frame(rows))
            return writer.commit()

    def read_rows(self, db, table_name):
        rows = db.table(table_name).order_by("id").execute()
        rows["modified"] = rows["modified"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return rows.to_dict("records")

    def test_writer_replace_mode(self):
        with self.patched_warehouse() as db:
            # First write — creates the table
            rows_written = self.write_to_table(
                db,
                "t",
                [
                    {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
            )
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "t"),
                [
                    {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
            )

            # Second write — table already exists; replace must overwrite, not silently drop data
            rows_written = self.write_to_table(
                db, "t", [{"id": 3, "value": "new", "modified": "2024-02-01 00:00:00"}]
            )
            self.assertEqual(rows_written, 1)
            self.assertEqual(
                self.read_rows(db, "t"),
                [{"id": 3, "value": "new", "modified": "2024-02-01 00:00:00"}],
            )

    def test_writer_append_mode_keeps_existing_rows(self):
        with self.patched_warehouse() as db:
            self.write_to_table(db, "t", [{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}])

            rows_written = self.write_to_table(
                db,
                "t",
                [
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                    {"id": 3, "value": "gamma", "modified": "2024-01-03 00:00:00"},
                ],
                mode="append",
            )
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "t"),
                [
                    {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                    {"id": 3, "value": "gamma", "modified": "2024-01-03 00:00:00"},
                ],
            )

    def test_writer_upsert_mode_updates_matching_primary_keys(self):
        with self.patched_warehouse() as db:
            self.write_to_table(db, "t", [{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}])

            rows_written = self.write_to_table(
                db,
                "t",
                [
                    {"id": 1, "value": "updated", "modified": "2024-01-02 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
                mode="upsert",
                primary_key_column="id",
                cursor_column="modified",
            )
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "t"),
                [
                    {"id": 1, "value": "updated", "modified": "2024-01-02 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
            )


class TestWarehouseWriteLock(InsightsIntegrationTestCase):
    """A writer must wait out the readers holding the warehouse file."""

    @contextmanager
    def warehouse_held_by_a_reader(self, hold_seconds):
        with tempfile.TemporaryDirectory(prefix="insights_lock_test_") as tmpdir:
            path = str(Path(tmpdir) / "warehouse.duckdb")
            open_local_duckdb(path, read_only=False).disconnect()

            reader = subprocess.Popen(
                [sys.executable, "-c", HOLD_READ_LOCK, path, str(hold_seconds)],
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                reader.stdout.readline()  # the reader holds the file from here
                yield path, tmpdir
            finally:
                reader.wait()

    def test_write_open_waits_for_a_reader_to_finish(self):
        with self.warehouse_held_by_a_reader(hold_seconds=3) as (path, tmpdir):
            started = time.monotonic()
            db = open_local_duckdb(path, read_only=False, allowed_dir=tmpdir, lock_timeout=60)
            waited = time.monotonic() - started
            try:
                db.raw_sql("create table t as select 1 as a")
            finally:
                db.disconnect()

            self.assertGreaterEqual(waited, 2, "the write open returned before the reader let go")

    def test_write_open_gives_up_at_the_timeout(self):
        with self.warehouse_held_by_a_reader(hold_seconds=2) as (path, tmpdir):
            with self.assertRaises(IOException) as caught:
                open_local_duckdb(path, read_only=False, allowed_dir=tmpdir, lock_timeout=1)

            self.assertIn("Could not set lock", str(caught.exception))


class TestMissingTableNotice(InsightsIntegrationTestCase):
    """A miss serves an empty table, so a failed import must not read as zero rows."""

    def make_table(self):
        return WarehouseTable("some_source", "some_table")

    def write_log(self, status):
        log = frappe.new_doc("Insights Table Import Log")
        log.data_source = "some_source"
        log.table_name = "some_table"
        log.status = status
        log.insert(ignore_permissions=True)
        return log

    def test_failed_import_tells_the_reader(self):
        self.write_log("Completed")
        self.write_log("Failed")

        with patch.object(insights, "create_toast") as toast:
            self.make_table().announce_missing_table()

        toast.assert_called_once()
        self.assertIn("some_table", toast.call_args.args[0])

    def test_running_import_stays_quiet(self):
        # enqueue_import already toasts this case; a second notice is noise.
        self.write_log("In Progress")

        with patch.object(insights, "create_toast") as toast:
            self.make_table().announce_missing_table()

        toast.assert_not_called()

    def test_a_table_that_never_imported_stays_quiet(self):
        with patch.object(insights, "create_toast") as toast:
            WarehouseTable("some_source", "never_imported").announce_missing_table()

        toast.assert_not_called()

    def test_a_queued_retry_suppresses_the_failure_notice(self):
        # The retry is queued but has not started, so the newest log still reads
        # "Failed" while enqueue_import already toasted "Import In Progress".
        self.write_log("Failed")

        with patch.object(insights, "create_toast") as toast:
            self.make_table().announce_missing_table(import_running=True)

        toast.assert_not_called()
