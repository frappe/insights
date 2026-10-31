import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager, suppress
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import duckdb
import frappe
import frappe.app
import ibis
import pandas as pd
import pyarrow as pa
from duckdb import ConversionException, IOException
from frappe.utils import add_to_date
from ibis.backends.duckdb import Backend as DuckDBBackend
from rq.job import JobStatus
from werkzeug.wrappers import Response

import insights
from insights.api.data_store import sync_tables, update_failed_sync_status
from insights.exceptions import QueryTimeout
from insights.insights.doctype.insights_data_source_v3 import data_warehouse
from insights.insights.doctype.insights_data_source_v3.connectors import duckdb as duckdb_connector
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import (
    connect_duckdb,
    get_memory_limit,
    open_local_duckdb,
)
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    WAREHOUSE_DB_NAME,
    WarehouseTable,
    WarehouseTableImporter,
    WarehouseTableWriter,
    data_store_pool,
    execute_warehouse_table_import,
    import_job_id,
)
from insights.insights.doctype.insights_data_source_v3.ibis_utils import execute_ibis_query
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    as_user,
    create_test_query,
    create_test_workbook,
    delete_workbooks,
)

GiB = 1024**3

# A second process reproduces the lock the web workers take in production.
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
    def test_writer_append_mode_keeps_rows_of_a_table_named_with_regex_characters(self):
        with self.patched_warehouse() as db:
            table = "orders_(eu)"
            self.write_to_table(db, table, [{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}])
            self.write_to_table(
                db, table, [{"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"}], mode="append"
            )
            self.assertEqual([row["id"] for row in self.read_rows(db, table)], [1, 2])

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

    def schema_tables(self, db, schema="main"):
        query = "select table_name from duckdb_tables() where database_name = current_database() and schema_name = ?"
        return {name for (name,) in db.raw_sql(query, parameters=[schema]).fetchall()}

    # @feature data-store.import-atomic
    def test_a_replace_that_fails_mid_insert_keeps_the_old_rows_and_no_other_table(self):
        with self.patched_warehouse() as db:
            self.write_to_table(db, "t", [{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}])

            # `id` is a BIGINT column, so the cast fails once the insert reaches "three"
            frame = pd.DataFrame(
                {"id": ["2", "three"], "value": ["beta", "gamma"], "modified": ["2024-01-02"] * 2}
            )
            frame["modified"] = pd.to_datetime(frame["modified"])
            with WarehouseTableWriter("t", table_schema=self.make_schema(), database="main") as writer:
                writer.insert(frame)
                with self.assertRaises(ConversionException):
                    writer.commit()

            self.assertEqual(self.schema_tables(db), {"t"})
            self.assertEqual(
                self.read_rows(db, "t"), [{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}]
            )

    # @feature data-store.run-without-import
    def test_dropping_a_table_whose_schema_was_never_created_does_nothing(self):
        # a fresh site's store has no schema until its first import
        with self.patched_warehouse() as db:
            WarehouseTable("Site DB", "tabToDo").drop()

            db.raw_sql("CREATE SCHEMA site_db")
            db.raw_sql("CREATE TABLE site_db.tabtodo AS SELECT 1 AS id")
            WarehouseTable("Site DB", "tabToDo").drop()
            self.assertNotIn("tabtodo", db.list_tables(database="site_db"))

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
    def test_write_open_waits_for_a_reader_in_this_process(self):
        with tempfile.TemporaryDirectory(prefix="insights_lock_test_") as tmpdir:
            path = str(Path(tmpdir) / "warehouse.duckdb")
            reader = open_local_duckdb(path)
            release = threading.Timer(2, reader.disconnect)
            release.start()
            started = time.monotonic()
            try:
                db = open_local_duckdb(path, read_only=False, allowed_dir=tmpdir, lock_timeout=60)
                waited = time.monotonic() - started
            finally:
                release.join()
            db.disconnect()

            self.assertGreaterEqual(waited, 1, "the write open returned before the reader let go")

    # @feature data-store.write-lock
    def test_write_open_gives_up_at_the_timeout(self):
        with self.warehouse_held_by_a_reader(hold_seconds=2) as (path, tmpdir):
            with self.assertRaises(IOException) as caught:
                open_local_duckdb(path, read_only=False, allowed_dir=tmpdir, lock_timeout=1)

            self.assertIn("Could not set lock", str(caught.exception))


class TestWarehouseSpillFolder(InsightsIntegrationTestCase):
    # @feature data-store.memory-limit
    def test_each_process_spills_into_its_own_folder(self):
        with tempfile.TemporaryDirectory(prefix="insights_spill_test_") as tmpdir:
            path = str(Path(tmpdir) / "warehouse.duckdb")
            folders = []
            for read_only in (False, True):
                db = open_local_duckdb(path, read_only=read_only)
                try:
                    folders.append(db.raw_sql("SELECT current_setting('temp_directory')").fetchone()[0])
                finally:
                    db.disconnect()
            other = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f"from {duckdb_connector.__name__} import get_temp_directory; print(get_temp_directory({path!r}))",
                ],
                capture_output=True,
                text=True,
                check=True,
                env=dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(insights.__file__))),
            ).stdout.strip()

        # DuckDB names spill files alike in every process, so a shared folder
        # lets one process delete or overwrite another's
        mine = os.path.join(f"{path}.tmp", str(os.getpid()))
        self.assertEqual(folders, [mine, mine])
        self.assertEqual(os.path.dirname(other), f"{path}.tmp")
        self.assertNotEqual(other, mine)


class TestWarehouseMemoryLimit(InsightsIntegrationTestCase):
    def memory_limits(self, path):
        connections = [
            lambda: open_local_duckdb(path, read_only=False),
            lambda: open_local_duckdb(path, read_only=True),
            connect_duckdb,
        ]
        limits = []
        for connect in connections:
            db = connect()
            try:
                limits.append(db.raw_sql("SELECT current_setting('memory_limit')").fetchone()[0])
            finally:
                db.disconnect()
        return limits

    # @feature data-store.memory-limit
    def test_every_duckdb_connection_is_held_to_the_memory_limit(self):
        with tempfile.TemporaryDirectory(prefix="insights_memory_test_") as tmpdir:
            path = str(Path(tmpdir) / "warehouse.duckdb")

            with patch.dict(frappe.conf, {"insights_duckdb_memory_limit": None}):
                with duckdb.connect(config={"memory_limit": get_memory_limit()}) as plain:
                    expected = plain.sql("SELECT current_setting('memory_limit')").fetchone()[0]
                self.assertEqual(self.memory_limits(path), [expected] * 3)

            with patch.dict(frappe.conf, {"insights_duckdb_memory_limit": "300MB"}):
                self.assertEqual(self.memory_limits(path), ["286.1 MiB"] * 3)

    # @feature data-store.memory-limit
    def test_a_read_connection_gets_its_share_of_the_servers_cores_memory_and_disk(self):
        # (cores, RAM) -> (slots, threads per query, memory per process)
        servers = {
            (2, 4 * GiB): (2, 1, GiB),
            (8, 31 * GiB): (3, 2, (31 - 2) * GiB // 2 // 3),
            (64, 256 * GiB): (12, 4, (256 - 2) * GiB // 2 // 12),
        }
        with tempfile.TemporaryDirectory(prefix="insights_budget_test_") as tmpdir:
            for i, ((cores, memory), (slots, threads, limit)) in enumerate(servers.items()):
                path = str(Path(tmpdir) / f"store{i}.duckdb")
                budget = {"cpu_budget": cores, "memory_budget": memory, "insights_duckdb_memory_limit": None}
                with (
                    patch.dict(frappe.conf, budget),
                    patch.object(duckdb_connector, "_free_disk", return_value=40 * GiB),
                ):
                    self.assertEqual(data_warehouse.data_store_slots(), slots)
                    db = open_local_duckdb(path, read_only=True)
                    try:
                        settings = db.raw_sql(
                            "SELECT current_setting('threads'), current_setting('memory_limit'),"
                            " current_setting('max_temp_directory_size')"
                        ).fetchone()
                    finally:
                        db.disconnect()
                    with duckdb.connect(
                        config={
                            "memory_limit": f"{limit}B",
                            "max_temp_directory_size": f"{10 * GiB // slots}B",
                        }
                    ) as plain:
                        expected = plain.sql(
                            "SELECT current_setting('memory_limit'), current_setting('max_temp_directory_size')"
                        ).fetchone()
                    self.assertEqual(settings, (threads, *expected), (cores, memory))


class TestDataStoreSlots(InsightsIntegrationTestCase):
    def before_test(self):
        self.addCleanup(self.close_store)
        self.close_store()
        patcher = patch.dict(frappe.conf, {"insights_data_store_slots": 2})
        patcher.start()
        self.addCleanup(patcher.stop)
        # the pool is shared by every site on this Redis: touch only this site's leases
        self.forget_leases()
        self.addCleanup(self.forget_leases)

    def forget_leases(self):
        for key in data_store_pool().keys:
            key = frappe.cache.make_key(key, shared=True)
            if mine := [
                m for m in frappe.cache.zrange(key, 0, -1) if m.decode().startswith(f"{frappe.local.site}|")
            ]:
                frappe.cache.zrem(key, *mine)

    def close_store(self):
        data_warehouse.release_data_store_slot()
        if db := insights.db_connections.pop(WAREHOUSE_DB_NAME, None):
            db.disconnect()

    @contextmanager
    def request(self):
        frappe.utils.set_request(method="POST", path="/api/method/insights.api.view.get_chart_data")
        frappe.local.response_headers = frappe.local.response_headers.__class__()
        response = Response(mimetype="application/json")
        try:
            yield
        except Exception:
            response.status_code = 500
            raise
        finally:
            # every app's hooks, as Frappe runs them after the response is built
            frappe.app.run_after_request_hooks(frappe.local.request, response)
            frappe.local.request = None

    def holders(self):
        return [h for h in data_store_pool().holders() if h.startswith(f"{frappe.local.site}|")]

    # @feature data-store.query-slots
    def test_a_request_holds_its_slot_from_opening_the_store_until_it_ends(self):
        with self.request():
            self.assertEqual(self.holders(), [])
            result, _ = execute_ibis_query(insights.warehouse.db.sql("select 42 as answer"), cache=False)
            # the rows are shaped after the query, inside the same slot
            self.assertEqual(result["answer"].tolist(), [42])
            self.assertEqual(len(self.holders()), 1)
            insights.warehouse.db.sql("select 1").execute()
            self.assertEqual(len(self.holders()), 1)

        self.assertEqual(self.holders(), [])

    # @feature data-store.query-slots
    def test_a_request_that_fails_gives_its_slot_back(self):
        with self.assertRaises(Exception), self.request():
            execute_ibis_query(insights.warehouse.db.sql("select cast('x' as integer) as n"), cache=False)

        self.assertEqual(self.holders(), [])

    # @feature data-store.query-slots
    def test_a_request_that_finds_every_slot_held_waits_then_is_answered_busy(self):
        pool = data_store_pool()
        held = []
        for user in ("one@example.com", "two@example.com"):
            with patch.object(frappe.local, "session", frappe._dict(user=user)):
                held.append(pool.acquire())
        self.assertTrue(all(held))

        with patch.object(data_warehouse, "SLOT_WAIT", 0.5), self.request():
            start = time.monotonic()
            with self.assertRaises(frappe.ServiceUnavailableError) as busy:
                insights.warehouse.db
            waited = time.monotonic() - start
            retry_after = frappe.local.response_headers.get("Retry-After")

        self.assertGreaterEqual(waited, 0.5)
        self.assertEqual((busy.exception.http_status_code, retry_after), (503, "2"))
        self.assertNotIn(WAREHOUSE_DB_NAME, insights.db_connections)

        # a query opens the store when it reads its first table
        with patch.object(data_warehouse, "SLOT_WAIT", 0), self.request():
            with self.assertRaises(frappe.ServiceUnavailableError):
                insights.warehouse.get_table("Site DB", "tabToDo").get_ibis_table()

    # @feature data-store.query-slots telemetry.query-failed
    def test_a_query_that_finds_every_slot_held_answers_busy_and_is_not_reported_as_failed(self):
        workbook = create_test_workbook("Administrator", title="Slot Test Workbook")
        self.addCleanup(delete_workbooks, title_prefix="Slot Test Workbook")
        query = create_test_query("Administrator", workbook.name)
        query.db_set("use_live_connection", 0)
        pool = data_store_pool()
        for user in ("one@example.com", "two@example.com"):
            with patch.object(frappe.local, "session", frappe._dict(user=user)):
                self.assertTrue(pool.acquire())

        with patch.object(data_warehouse, "SLOT_WAIT", 0), self.request():
            with patch("frappe.utils.telemetry.capture") as sender:
                with self.assertRaises(frappe.ServiceUnavailableError) as busy:
                    query.execute()

        # the build does not reword it as a broken operation
        self.assertNotIn("Operation", str(busy.exception))
        self.assertNotIn("query_failed", [call.args[0] for call in sender.call_args_list])

    # @feature data-store.query-slots
    def test_a_process_holds_one_slot_however_many_threads_it_serves(self):
        with self.request():
            insights.warehouse.db
            first = frappe.local.insights_data_store_slot
            # another request in this process, while the first still holds its slot
            frappe.local.insights_data_store_slot = None
            with patch.object(data_warehouse, "SLOT_WAIT", 0.3):
                with self.assertRaises(frappe.ServiceUnavailableError):
                    data_warehouse.take_data_store_slot()
            # the pool had room: the process's own slot turned it away
            self.assertEqual(len(self.holders()), 1)
            frappe.local.insights_data_store_slot = first

        self.assertEqual(self.holders(), [])
        with self.request():
            insights.warehouse.db
            self.assertEqual(len(self.holders()), 1)

    # @feature data-store.query-slots
    def test_a_process_slot_whose_release_never_ran_frees_itself_after_a_lease(self):
        slot = data_warehouse.ProcessSlot()
        stale = slot.acquire(wait=0, hold=0.2)
        self.assertIsNone(slot.acquire(wait=0, hold=0.2))
        time.sleep(0.25)
        fresh = slot.acquire(wait=0, hold=60)
        self.assertTrue(fresh)
        # the late release of the first holder leaves the second one holding
        slot.release(stale)
        self.assertIsNone(slot.acquire(wait=0, hold=60))
        slot.release(fresh)
        self.assertTrue(slot.acquire(wait=0, hold=60))

    # @feature data-store.time-limit
    def test_a_request_that_runs_several_queries_shares_the_web_tiers_time_among_them(self):
        with patch.object(data_warehouse, "web_tier_setting", return_value=120), self.request():
            insights.warehouse.db
            self.assertEqual(data_warehouse.get_data_store_time_limit(), 60)
            pool, lease, started, process_slot = frappe.local.insights_data_store_slot
            frappe.local.insights_data_store_slot = (pool, lease, started - 49.5, process_slot)
            self.assertEqual(data_warehouse.get_data_store_time_limit(), 40)

    # @feature data-store.query-slots
    def test_a_background_job_reads_the_store_without_a_slot(self):
        self.assertIsNone(getattr(frappe.local, "request", None))
        insights.warehouse.db.sql("select 1").execute()

        self.assertEqual(self.holders(), [])


class TestDataStoreTimeLimit(InsightsIntegrationTestCase):
    SAVEPOINT = "test_data_store_time_limit"
    SLOW_QUERY = "select sum(a.range * b.range % 7) as n from range(100000) a, range(100000) b"

    def before_test(self):
        original = frappe.db.get_single_value("Insights Settings", "max_execution_time")
        # the class commits when it ends, so a rollback alone would keep the change
        self.addCleanup(frappe.db.set_single_value, "Insights Settings", "max_execution_time", original)
        frappe.db.set_single_value("Insights Settings", "max_execution_time", 1)
        self.db = insights.warehouse.db
        # stops the query should the limit not, so a failing test ends
        guard = threading.Timer(30, self.db.con.interrupt)
        guard.start()
        self.addCleanup(guard.cancel)

    # @feature data-store.time-limit
    def test_a_data_store_query_stops_at_max_execution_time_and_the_connection_runs_the_next(self):
        start = time.monotonic()
        with self.assertRaises(QueryTimeout) as timeout:
            execute_ibis_query(self.db.sql(self.SLOW_QUERY), cache=False)

        self.assertLess(time.monotonic() - start, 10)
        self.assertIn("exceeded the limit of 1 seconds", str(timeout.exception))
        result, _ = execute_ibis_query(self.db.sql("select 7 as n"), cache=False)
        self.assertEqual(result["n"].tolist(), [7])

    # @feature data-store.time-limit
    def test_a_query_never_outlives_the_web_tiers_timeout(self):
        frappe.db.set_single_value("Insights Settings", "max_execution_time", 600)
        with patch.object(data_warehouse, "web_tier_setting", return_value=2):
            with self.assertRaises(QueryTimeout) as timeout:
                execute_ibis_query(self.db.sql(self.SLOW_QUERY), cache=False)

        self.assertIn("exceeded the limit of 1 seconds", str(timeout.exception))


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


class TestSyncSchedule(InsightsIntegrationTestCase):
    TABLE = "sync_schedule_table"
    # one more due table than the site imports at once
    TABLES = (TABLE, "sync_schedule_table_2", "sync_schedule_table_3")
    OTHER_TABLE = "sync_schedule_other_table"
    # an @hourly table falls due on the hour, so a moving clock would decide the outcome
    HALF_PAST = datetime(2026, 1, 1, 12, 30)

    @classmethod
    def before_class(cls):
        for table in cls.TABLES:
            frappe.get_doc(
                {
                    "doctype": "Insights Table v3",
                    "table": table,
                    "label": table,
                    "data_source": "Site DB",
                    "stored": 1,
                    "sync_schedule": "@hourly",
                }
            ).insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        for table in cls.TABLES:
            frappe.delete_doc("Insights Table v3", get_table_name("Site DB", table), force=True)

    def after_test(self):
        frappe.db.delete(
            "Insights Table Import Log", {"table_name": ["in", [*self.TABLES, self.OTHER_TABLE]]}
        )

    def start_import(self, minutes_ago, status, table=TABLE):
        log = frappe.new_doc("Insights Table Import Log")
        log.data_source = "Site DB"
        log.table_name = table
        log.status = status
        log.started_at = add_to_date(self.HALF_PAST, minutes=-minutes_ago)
        log.insert(ignore_permissions=True)

    def make_all_due(self):
        for table in self.TABLES:
            self.start_import(minutes_ago=120, status="Completed", table=table)

    @contextmanager
    def enqueued_tables(self, users=None):
        tables, users = [], [] if users is None else users
        with (
            patch(
                "frappe.enqueue", side_effect=lambda *args, **kwargs: users.append(frappe.session.user)
            ) as enqueue,
            patch("insights.api.data_store.now_datetime", return_value=self.HALF_PAST),
        ):
            yield tables
        tables.extend(call.kwargs.get("table_name") for call in enqueue.call_args_list)

    def imported_tables(self):
        with self.enqueued_tables() as tables:
            sync_tables()
        return tables

    # @feature data-store.sync-schedule
    def test_a_table_is_imported_once_its_schedule_is_due_since_its_last_import(self):
        self.start_import(minutes_ago=120, status="Completed")
        self.assertIn(self.TABLE, self.imported_tables())

    # @feature data-store.sync-schedule
    def test_a_failed_import_waits_for_the_next_due_time_instead_of_retrying_every_tick(self):
        self.start_import(minutes_ago=120, status="Completed")
        self.start_import(minutes_ago=10, status="Failed")
        self.assertNotIn(self.TABLE, self.imported_tables())

    # @feature data-store.import-concurrency
    def test_no_more_than_two_due_tables_are_imported_at_once(self):
        self.make_all_due()
        self.assertEqual(len(self.imported_tables()), 2)

    # @feature data-store.import-concurrency
    def test_the_tables_that_have_waited_longest_are_imported_first(self):
        # the table list sorts the last edited first, and here it has waited least
        for order, table in enumerate(self.TABLES):
            self.start_import(minutes_ago=90 + 60 * order, status="Completed", table=table)
            frappe.db.set_value(
                "Insights Table v3",
                get_table_name("Site DB", table),
                "modified",
                add_to_date(None, minutes=-order),
                update_modified=False,
            )
        self.assertEqual(self.imported_tables(), [self.TABLES[2], self.TABLES[1]])

    # @feature data-store.import-concurrency
    def test_an_import_under_way_holds_one_of_the_two_places(self):
        self.make_all_due()
        self.start_import(minutes_ago=5, status="In Progress", table=self.OTHER_TABLE)
        self.assertEqual(len(self.imported_tables()), 1)

    # @feature data-store.import-concurrency
    def test_imports_queued_but_not_started_hold_their_places(self):
        self.make_all_due()
        queued = {import_job_id("Site DB", table) for table in self.TABLES[1:]}
        with patch(
            "insights.api.data_store.get_job_status",
            side_effect=lambda job_id: JobStatus.QUEUED if job_id in queued else None,
        ):
            self.assertEqual(self.imported_tables(), [])

    # @feature data-store.import-concurrency
    def test_an_import_whose_worker_died_frees_its_place_after_the_job_timeout(self):
        self.make_all_due()
        self.start_import(minutes_ago=31, status="In Progress", table=self.OTHER_TABLE)
        self.assertEqual(len(self.imported_tables()), 2)

    # @feature data-store.import-concurrency
    def test_the_next_due_table_is_imported_as_an_import_ends_even_a_failed_one(self):
        self.start_import(minutes_ago=120, status="Completed")
        users = []
        # a reader whose query found its table missing queued the import that ends
        with as_user("Guest"), self.enqueued_tables(users) as tables:
            with patch.object(
                WarehouseTableImporter, "start_import", side_effect=RuntimeError("source went away")
            ):
                with self.assertRaises(RuntimeError):
                    execute_warehouse_table_import("Site DB", self.OTHER_TABLE)
            self.assertEqual(frappe.session.user, "Guest")
        self.assertEqual(tables, [self.TABLE])
        self.assertEqual(users, ["Administrator"])

    # @feature data-store.killed-import-reason
    def test_an_import_whose_worker_was_killed_fails_and_says_why(self):
        self.start_import(minutes_ago=0, status="In Progress")
        log = frappe.get_last_doc("Insights Table Import Log", {"table_name": self.TABLE})
        # a killed worker leaves its log In Progress, and the hourly check looks an hour back
        log.db_set("creation", self.HALF_PAST, update_modified=False)

        update_failed_sync_status()

        log.reload()
        self.assertEqual(log.status, "Failed")
        self.assertIn("worker was killed or restarted", log.output)


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


class TestSiteDBImport(InsightsIntegrationTestCase):
    """An import from MariaDB reads each batch a chunk at a time."""

    DATA_SOURCE = "Site DB"
    TABLE = "tabDocField"
    SETTINGS = ("stored", "sync_mode", "row_limit", "before_import_script")

    @classmethod
    def before_class(cls):
        cls.table_doc = get_table_name(cls.DATA_SOURCE, cls.TABLE)
        cls.made_doc = not frappe.db.exists("Insights Table v3", cls.table_doc)
        if cls.made_doc:
            doc = frappe.get_doc(
                {
                    "doctype": "Insights Table v3",
                    "table": cls.TABLE,
                    "label": cls.TABLE,
                    "data_source": cls.DATA_SOURCE,
                }
            )
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True)
        cls.settings_were = frappe.db.get_value(
            "Insights Table v3", cls.table_doc, cls.SETTINGS, as_dict=True
        )
        frappe.db.set_value(
            "Insights Table v3",
            cls.table_doc,
            {"sync_mode": "Full", "row_limit": 0, "before_import_script": None},
        )

    @classmethod
    def after_class(cls):
        if cls.made_doc:
            frappe.delete_doc("Insights Table v3", cls.table_doc, force=True, ignore_permissions=True)
        else:
            frappe.db.set_value("Insights Table v3", cls.table_doc, cls.settings_were)
        frappe.db.delete(
            "Insights Table Import Log", {"table_name": cls.TABLE, "creation": [">=", cls.started]}
        )
        frappe.db.commit()  # nosemgrep - the import commits its logs and these settings, so undoing them must commit too

    def before_test(self):
        TestSiteDBImport.started = frappe.utils.now()
        tmpdir = tempfile.mkdtemp(prefix="insights_site_db_import_test_")
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        self.path = str(Path(tmpdir) / "store.duckdb")
        self.enterContext(patch.object(insights.warehouse, "get_db_path", return_value=self.path))
        self.enterContext(patch.object(insights, "create_toast"))
        self.enterContext(patch("frappe.utils.telemetry.capture"))
        insights.db_connections.pop("insights", None)

    # @feature data-store.import-table
    def test_an_import_from_mariadb_copies_each_row_once_across_chunks_and_batches(self):
        # a doctype's fields share a creation and outnumber a chunk of a 1000-row batch
        with patch.object(WarehouseTableImporter, "calculate_batch_size", return_value=1000):
            WarehouseTableImporter(WarehouseTable(self.DATA_SOURCE, self.TABLE)).start_import()

        source = frappe.db.sql("SELECT * FROM `tabDocField` ORDER BY name", as_list=True)
        db = open_local_duckdb(self.path)
        try:
            stored = db.raw_sql("SELECT * FROM site_db.tabdocfield ORDER BY name").fetchall()
        finally:
            db.disconnect()
        self.assertEqual([tuple(row) for row in source], stored)


HOLD_WRITE_LOCK = """
import sys, time, duckdb
con = duckdb.connect(sys.argv[1])
print("held", flush=True)
time.sleep(float(sys.argv[2]))
con.close()
"""


class TestIncrementalImport(InsightsIntegrationTestCase):
    """An incremental import copies each source row once, from Sync From on."""

    DATA_SOURCE = "Site DB"
    TABLE = "incremental_import_table"

    @classmethod
    def before_class(cls):
        doc = frappe.get_doc(
            {
                "doctype": "Insights Table v3",
                "table": cls.TABLE,
                "label": cls.TABLE,
                "data_source": cls.DATA_SOURCE,
                "sync_mode": "Incremental",
                "sync_strategy": "Append Only",
                "sync_cursor_column": "creation",
                "sync_from": "2026-01-01 00:00:00",
            }
        )
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        cls.table_doc = doc.name

    @classmethod
    def after_class(cls):
        frappe.delete_doc("Insights Table v3", cls.table_doc, force=True, ignore_permissions=True)
        frappe.db.delete("Insights Table Import Log", {"table_name": cls.TABLE})

    def before_test(self):
        tmpdir = tempfile.mkdtemp(prefix="insights_incremental_test_")
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        self.path = str(Path(tmpdir) / "incremental.duckdb")
        self.enterContext(patch.object(insights.warehouse, "get_db_path", return_value=self.path))
        self.enterContext(patch.object(insights, "create_toast"))
        self.enterContext(patch("frappe.utils.telemetry.capture"))
        insights.db_connections.pop("insights", None)
        frappe.db.set_value(
            "Insights Table v3",
            self.table_doc,
            {
                "stored": 0,
                "row_limit": 0,
                "sync_mode": "Incremental",
                "sync_strategy": "Append Only",
                "sync_cursor_column": "creation",
                "sync_primary_key_column": None,
                "sync_from": "2026-01-01 00:00:00",
                "last_sync_bookmark": None,
            },
        )

    def run_import(self, names, creations=None):
        creations = creations or [f"2026-02-0{ord(name) - 96} 10:00:00.123456" for name in names]
        self.import_source(pd.DataFrame({"name": names, "creation": pd.to_datetime(creations)}))

    def import_source(self, rows):
        with patch.object(WarehouseTable, "get_remote_table", return_value=ibis.memtable(rows)):
            WarehouseTableImporter(WarehouseTable(self.DATA_SOURCE, self.TABLE)).start_import()

    def stored_names(self):
        return self.stored_rows()["name"].to_pylist()

    def stored_rows(self):
        db = open_local_duckdb(self.path)
        try:
            return db.table("incremental_import_table", database="site_db").to_pyarrow().sort_by("name")
        finally:
            db.disconnect()

    @contextmanager
    def another_writer_after_each_commit(self):
        """Another import takes the file the moment this one releases it, as on a busy queue."""
        holders = []
        commit = WarehouseTableWriter.commit

        def commit_then_hand_over(writer):
            rows = commit(writer)
            holder = subprocess.Popen(
                [sys.executable, "-c", HOLD_WRITE_LOCK, self.path, "30"], stdout=subprocess.PIPE, text=True
            )
            self.assertEqual(holder.stdout.readline().strip(), "held")
            holders.append(holder)
            return rows

        try:
            with patch.object(WarehouseTableWriter, "commit", commit_then_hand_over):
                yield
        finally:
            for holder in holders:
                holder.kill()
                holder.wait()

    # @feature data-store.import-cursor
    def test_a_row_is_copied_once_when_another_writer_holds_the_store_after_the_commit(self):
        with self.another_writer_after_each_commit():
            self.run_import(["a", "b"])
        self.run_import(["a", "b", "c"])

        self.assertEqual(self.stored_names(), ["a", "b", "c"])

    # @feature data-store.import-cursor
    def test_a_capped_full_table_switched_to_incremental_imports_from_sync_from(self):
        frappe.db.set_value("Insights Table v3", self.table_doc, {"sync_mode": "Full", "row_limit": 2})
        self.run_import(["a", "b", "c", "d"])
        self.assertEqual(self.stored_names(), ["c", "d"])

        doc = frappe.get_doc("Insights Table v3", self.table_doc)
        doc.update(
            {
                "sync_mode": "Incremental",
                "sync_strategy": "Update or Insert",
                "sync_primary_key_column": "name",
            }
        )
        doc.save(ignore_permissions=True)
        self.run_import(["a", "b", "c", "d"])

        self.assertEqual(self.stored_names(), ["a", "b", "c", "d"])

    # @feature data-store.import-cursor
    def test_sync_settings_cannot_change_while_the_table_is_imported(self):
        frappe.db.set_value("Insights Table v3", self.table_doc, "sync_mode", "Full")
        log = frappe.get_doc(
            {
                "doctype": "Insights Table Import Log",
                "data_source": self.DATA_SOURCE,
                "table_name": self.TABLE,
                "status": "In Progress",
            }
        ).insert(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "Insights Table Import Log", log.name, force=True)

        # the first import stores nothing until it commits
        doc = frappe.get_doc("Insights Table v3", self.table_doc)
        doc.sync_mode = "Incremental"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

        self.run_import(["a", "b"])
        doc.reload()
        doc.sync_mode = "Incremental"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

        self.assertEqual(self.stored_names(), ["a", "b"])

    # @feature data-store.import-cursor
    def test_a_first_incremental_import_waits_for_another_writer(self):
        open_local_duckdb(self.path, read_only=False).disconnect()
        holder = subprocess.Popen(
            [sys.executable, "-c", HOLD_WRITE_LOCK, self.path, "2"], stdout=subprocess.PIPE, text=True
        )
        self.addCleanup(holder.wait)
        self.assertEqual(holder.stdout.readline().strip(), "held")

        self.run_import(["a", "b"])

        self.assertEqual(self.stored_names(), ["a", "b"])

    # @feature data-store.import-cursor
    def test_a_sync_from_change_on_an_incremental_table_keeps_its_rows(self):
        self.run_import(["a", "b"])

        doc = frappe.get_doc("Insights Table v3", self.table_doc)
        doc.sync_from = "2025-01-01 00:00:00"
        doc.save(ignore_permissions=True)
        # the source has purged a since
        self.run_import(["b", "c"])

        self.assertEqual(self.stored_names(), ["a", "b", "c"])

    # @feature data-store.import-cursor
    def test_the_cursor_cannot_change_to_a_column_the_stored_rows_lack(self):
        self.run_import(["a", "b"])

        doc = frappe.get_doc("Insights Table v3", self.table_doc)
        doc.sync_cursor_column = "modified"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

        self.assertEqual(self.stored_names(), ["a", "b"])

    # @feature data-store.import-cursor
    def test_rows_sharing_the_cursor_at_a_batch_boundary_are_copied_once(self):
        with patch.object(WarehouseTableImporter, "calculate_batch_size", return_value=2):
            self.run_import(
                ["a", "b", "c", "d", "e"],
                ["2026-02-01", "2026-02-02", "2026-02-02", "2026-02-02", "2026-02-03"],
            )

        self.assertEqual(self.stored_names(), ["a", "b", "c", "d", "e"])

    # @feature data-store.import-cursor
    def test_a_row_committed_later_at_the_stored_cursor_is_copied_once(self):
        self.run_import(["a", "b"], ["2026-02-01", "2026-02-02"])
        self.run_import(["a", "b", "c"], ["2026-02-01", "2026-02-02", "2026-02-02"])

        self.assertEqual(self.stored_names(), ["a", "b", "c"])

    # @feature data-store.import-cursor
    def test_a_row_committed_later_at_the_stored_cursor_is_merged_once(self):
        frappe.db.set_value(
            "Insights Table v3",
            self.table_doc,
            {"sync_strategy": "Update or Insert", "sync_primary_key_column": "name"},
        )
        self.run_import(["a", "b"], ["2026-02-01", "2026-02-02"])
        self.run_import(["a", "b", "c"], ["2026-02-01", "2026-02-02", "2026-02-02"])

        self.assertEqual(self.stored_names(), ["a", "b", "c"])

    # @feature data-store.import-cursor
    def test_a_merged_row_keeps_a_column_the_source_no_longer_reads(self):
        frappe.db.set_value(
            "Insights Table v3",
            self.table_doc,
            {"sync_strategy": "Update or Insert", "sync_primary_key_column": "name"},
        )
        creations = pd.to_datetime(["2026-02-01", "2026-02-02"])
        self.import_source(pd.DataFrame({"name": ["a", "b"], "creation": creations, "remarks": ["x", "y"]}))
        self.import_source(pd.DataFrame({"name": ["a", "b"], "creation": creations}))

        self.assertEqual(self.stored_rows()["remarks"].to_pylist(), ["x", "y"])

    # @feature data-store.import-cursor
    def test_a_row_without_a_key_at_the_stored_cursor_is_merged_once(self):
        frappe.db.set_value(
            "Insights Table v3",
            self.table_doc,
            {"sync_strategy": "Update or Insert", "sync_primary_key_column": "name"},
        )
        for _run in range(3):
            self.run_import(["a", None], ["2026-02-01", "2026-02-02"])

        self.assertEqual(self.stored_names(), ["a", None])

    # @feature data-store.import-cursor
    def test_a_failed_commit_keeps_the_stored_rows(self):
        self.run_import(["a", "b"], ["2026-02-01", "2026-02-02"])

        with patch.object(DuckDBBackend, "insert", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                self.run_import(["a", "b", "c"], ["2026-02-01", "2026-02-02", "2026-02-02"])

        self.assertEqual(self.stored_names(), ["a", "b"])

    # @feature data-store.import-cursor
    def test_rows_without_a_cursor_value_are_copied_with_the_rest(self):
        frappe.db.set_value("Insights Table v3", self.table_doc, "sync_mode", "Full")
        with patch.object(WarehouseTableImporter, "calculate_batch_size", return_value=2):
            self.run_import(["a", "b", "c", "d", "e"], [None, None, None, "2026-02-01", "2026-02-02"])

        self.assertEqual(self.stored_names(), ["a", "b", "c", "d", "e"])

    @contextmanager
    def commit_running_out_of_memory(self, times):
        """Commit with a 600 MB limit, and run out of memory the first `times` times.

        It runs out after the rows at the bookmark are deleted, so the rollback has
        work to undo.
        """
        get_single_value = frappe.db.get_single_value
        commit, insert = WarehouseTableWriter._commit, DuckDBBackend.insert
        limits, threads = [], []

        def commit_with(writer, memory):
            limits.append(memory)
            return commit(writer, memory)

        def insert_or_run_out(db, *args, **kwargs):
            threads.append(db.raw_sql("SELECT current_setting('threads')").fetchone()[0])
            if len(limits) <= times:
                raise duckdb.OutOfMemoryException("Out of Memory Error: could not allocate block")
            return insert(db, *args, **kwargs)

        with (
            patch.dict(frappe.conf, {"insights_duckdb_memory_limit": None}),
            patch.object(
                frappe.db,
                "get_single_value",
                side_effect=lambda doctype, field, *args, **kwargs: 600
                if field == "max_memory_usage"
                else get_single_value(doctype, field, *args, **kwargs),
            ),
            patch.object(WarehouseTableWriter, "_commit", autospec=True, side_effect=commit_with),
            patch.object(DuckDBBackend, "insert", autospec=True, side_effect=insert_or_run_out),
        ):
            yield limits, threads

    # @feature data-store.import-table
    def test_a_commit_that_runs_out_of_its_share_of_memory_runs_again_with_the_whole_limit(self):
        self.run_import(["a", "b"], ["2026-02-01", "2026-02-02"])
        with self.commit_running_out_of_memory(times=1) as (limits, threads):
            self.run_import(["a", "b", "c"], ["2026-02-01", "2026-02-02", "2026-02-02"])

        self.assertEqual(self.stored_names(), ["a", "b", "c"])
        self.assertEqual(limits, [400, 600])
        self.assertEqual(threads, [1, 1])

    # @feature data-store.import-table
    def test_a_commit_that_runs_out_of_the_whole_limit_fails_and_says_to_raise_it(self):
        self.run_import(["a", "b"], ["2026-02-01", "2026-02-02"])
        with self.commit_running_out_of_memory(times=2) as (limits, _):
            with self.assertRaisesRegex(duckdb.OutOfMemoryException, "Raise Max Memory Usage"):
                self.run_import(["a", "b", "c"], ["2026-02-01", "2026-02-02", "2026-02-02"])

        self.assertEqual(self.stored_names(), ["a", "b"])
        self.assertEqual(limits, [400, 600])
        log = frappe.get_last_doc("Insights Table Import Log", {"table_name": self.TABLE})
        self.assertEqual(log.status, "Failed")
        self.assertIn("needs more than 600 MB. Raise Max Memory Usage in Insights Settings", log.output)

    # @feature data-store.import-table
    def test_a_column_empty_in_one_batch_keeps_its_source_type(self):
        frappe.db.set_value("Insights Table v3", self.table_doc, "sync_mode", "Full")
        rows = pa.table(
            {
                "name": ["a", "b", "c", "d"],
                "creation": pa.array([datetime(2026, 2, i) for i in range(1, 5)], pa.timestamp("us")),
                "remarks": pa.array([None, None, "late", "later"], pa.string()),
                "amount": pa.array([None, Decimal("1.50"), None, Decimal("2.25")], pa.decimal128(18, 2)),
            }
        )
        with patch.object(WarehouseTableImporter, "calculate_batch_size", return_value=2):
            self.import_source(rows)

        stored = self.stored_rows()
        self.assertEqual(stored["remarks"].to_pylist(), [None, None, "late", "later"])
        self.assertEqual(stored["amount"].type, pa.decimal128(18, 2))
