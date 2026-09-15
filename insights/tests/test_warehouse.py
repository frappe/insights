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
    WarehouseTableImporter,
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

    # @feature data-store.import-table
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

    # @feature data-store.import-table
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

    # @feature data-store.import-table
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

    # @feature data-store.division-by-zero
    def test_a_division_by_zero_returns_null_as_on_the_live_connection(self):
        with self.warehouse_db() as db:
            row = db.sql("SELECT 5.0 / 0 AS positive, -5 / 0 AS negative, 0 / 0 AS undefined").execute()
            self.assertEqual(
                row.isna().to_dict("records"), [{"positive": True, "negative": True, "undefined": True}]
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

    # @feature data-store.write-lock
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

    # @feature data-store.write-lock
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

    # @feature data-store.failed-import-notice
    def test_failed_import_tells_the_reader(self):
        self.write_log("Completed")
        self.write_log("Failed")

        with patch.object(insights, "create_toast") as toast:
            self.make_table().announce_missing_table()

        toast.assert_called_once()
        self.assertIn("some_table", toast.call_args.args[0])

    # @feature data-store.failed-import-notice
    def test_running_import_stays_quiet(self):
        # enqueue_import already toasts this case; a second notice is noise.
        self.write_log("In Progress")

        with patch.object(insights, "create_toast") as toast:
            self.make_table().announce_missing_table()

        toast.assert_not_called()

    # @feature data-store.failed-import-notice
    def test_a_table_that_never_imported_stays_quiet(self):
        with patch.object(insights, "create_toast") as toast:
            WarehouseTable("some_source", "never_imported").announce_missing_table()

        toast.assert_not_called()

    # @feature data-store.failed-import-notice
    def test_a_queued_retry_suppresses_the_failure_notice(self):
        # The retry is queued but has not started, so the newest log still reads
        # "Failed" while enqueue_import already toasted "Import In Progress".
        self.write_log("Failed")

        with patch.object(insights, "create_toast") as toast:
            self.make_table().announce_missing_table(import_running=True)

        toast.assert_not_called()


class TestImportRowLimit(InsightsIntegrationTestCase):
    """How many rows an import is allowed to copy.

    The cap is the table's own `row_limit`, then the site's `max_records_to_sync`.
    `apply_limit` is what puts it on the read, so the number that is resolved and
    the rows that survive it are checked together.
    """

    DATA_SOURCE = "Site DB"
    CAPPED = "row_limit_capped_table"
    UNCAPPED = "row_limit_uncapped_table"

    @classmethod
    def before_class(cls):
        cls.site_limit_was = frappe.db.get_single_value("Insights Settings", "max_records_to_sync")
        for table_name, row_limit in ((cls.CAPPED, 2), (cls.UNCAPPED, 0)):
            doc = frappe.get_doc(
                {
                    "doctype": "Insights Table v3",
                    "table": table_name,
                    "label": table_name,
                    "data_source": cls.DATA_SOURCE,
                    "sync_mode": "Full",
                    "row_limit": row_limit,
                }
            )
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        frappe.db.set_single_value("Insights Settings", "max_records_to_sync", cls.site_limit_was)
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

        for table_name in (cls.CAPPED, cls.UNCAPPED):
            name = get_table_name(cls.DATA_SOURCE, table_name)
            if frappe.db.exists("Insights Table v3", name):
                frappe.delete_doc("Insights Table v3", name, force=True, ignore_permissions=True)

    def five_rows(self):
        return ibis.memtable(pd.DataFrame({"id": [1, 2, 3, 4, 5]}))

    def importer_for(self, table_name):
        importer = WarehouseTableImporter(WarehouseTable(self.DATA_SOURCE, table_name))
        importer.prepare_log()
        self.addCleanup(
            frappe.delete_doc,
            "Insights Table Import Log",
            importer.log.name,
            force=True,
            ignore_permissions=True,
        )
        importer.prepare_settings()
        return importer

    def rows_kept_by(self, importer):
        return len(importer.apply_limit(self.five_rows()).execute())

    # @feature data-store.import-row-limit
    def test_an_import_copies_no_more_rows_than_the_tables_row_limit(self):
        frappe.db.set_single_value("Insights Settings", "max_records_to_sync", 0)

        capped = self.importer_for(self.CAPPED)
        self.assertEqual(capped.settings.row_limit, 2)
        self.assertEqual(self.rows_kept_by(capped), 2)

        # a table that names no cap, on a site that names none either, keeps them all
        uncapped = self.importer_for(self.UNCAPPED)
        self.assertEqual(uncapped.settings.row_limit, 10_00_000)
        self.assertEqual(self.rows_kept_by(uncapped), 5)

    # @feature settings.data-store-enable
    def test_an_import_without_its_own_limit_falls_back_to_the_sites_row_limit(self):
        frappe.db.set_single_value("Insights Settings", "max_records_to_sync", 3)

        uncapped = self.importer_for(self.UNCAPPED)
        self.assertEqual(uncapped.settings.row_limit, 3)
        self.assertEqual(self.rows_kept_by(uncapped), 3)

        # the table's own limit still outranks the site's
        capped = self.importer_for(self.CAPPED)
        self.assertEqual(capped.settings.row_limit, 2)
        self.assertEqual(self.rows_kept_by(capped), 2)
