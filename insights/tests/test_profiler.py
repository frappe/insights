import os
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import duckdb
import frappe

import insights
from insights.api import profiler as profiler_api
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import open_local_duckdb
from insights.insights.doctype.insights_data_source_v3.ibis_utils import execute_ibis_query
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.profiler import events, report, statement, targets
from insights.profiler.recorder import process_stamp
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

OWNER = "profiler_owner@test.com"
# holds an Insights role, not the admin role the profiler asks for
READER = "profiler_reader@test.com"
WORKBOOK_TITLE = "Profiler Test Workbook"
FILTER_DEFAULT = "Profiler Test default"
LOG = "Insights Query Execution Log"

# A writer in another process holds the file's lock, as an import in a
# background worker holds it against the web workers in production.
HOLD_WRITE_LOCK = """
import sys, time, duckdb
con = duckdb.connect(sys.argv[1])
print("held", flush=True)
time.sleep(float(sys.argv[2]))
"""


class TestProfilerRecorder(InsightsIntegrationTestCase):
    def setUp(self):
        events.start_recording(5)
        self.since = time.time()

    def tearDown(self):
        events.stop_recording()

    def recorded(self, dashboard: str | None = None, since: float | None = None):
        return report.summarize(since or self.since, time.time() + 1, dashboard=dashboard)

    def query_start(self, sql: str, ts: float, dashboard: str, **process) -> dict:
        """A query start as a request for `dashboard` writes it.

        Written events stay on disk for the day, so each test names its own
        dashboard and reads back only that.
        """
        return {
            "id": uuid4().hex[:16],
            "kind": "query",
            "ts": ts,
            "site": frappe.local.site,
            "sql": sql,
            "source": "data_store",
            "cache": "miss",
            "dashboard": dashboard,
            **process,
        }

    # @feature data-store.profiler-recorder
    def test_a_store_query_that_fails_is_kept_with_its_error_and_its_sql(self):
        with db_connections(), self.assertRaises(duckdb.ConversionException):
            execute_ibis_query(insights.warehouse.db.sql("SELECT CAST('x' AS INTEGER) AS n"), force=True)

        found = self.recorded()
        self.assertEqual(found["queries"]["by_state"], {"failed: ConversionException": 1})
        [failure] = found["failures"]
        self.assertEqual((failure["state"], failure["error_type"]), ("failed", "ConversionException"))
        self.assertIn("CAST('x' AS INT", events.read_sql(failure["sql"]))

    # @feature data-store.profiler-recorder
    def test_a_read_a_writers_lock_refuses_is_kept_as_refused_by_the_lock(self):
        with tempfile.TemporaryDirectory(prefix="insights_profiler_test_") as folder:
            path = os.path.join(folder, "held.duckdb")
            duckdb.connect(path).close()
            holder = subprocess.Popen(
                [sys.executable, "-c", HOLD_WRITE_LOCK, path, "10"], stdout=subprocess.PIPE, text=True
            )
            try:
                holder.stdout.readline()
                with self.assertRaises(duckdb.IOException):
                    open_local_duckdb(path)
            finally:
                holder.kill()
                holder.wait()

        connections = self.recorded()["connections"]
        self.assertEqual(
            (connections["count"], connections["refused"], connections["refused_by_lock"]), (1, 1, 1)
        )

    # @feature data-store.profiler-recorder
    def test_work_a_killed_worker_never_finished_reads_as_killed(self):
        gone = subprocess.Popen([sys.executable, "-c", "pass"])
        gone.wait()
        this_process, mine, base = process_stamp(), uuid4().hex, time.time() - 10
        # a query whose worker died with it in hand
        events.write(self.query_start("aaaa", base, mine, pid=gone.pid, pid_started=0.0, thread=0))
        # a query whose end was lost, by a worker that went on to write more
        events.write(self.query_start("bbbb", base + 1, mine, **this_process))
        events.write({"id": uuid4().hex[:16], "kind": "connect", "ts": base + 2, **this_process, "ok": True})

        found = self.recorded(dashboard=mine, since=base - 1)
        self.assertEqual(found["queries"]["by_state"], {"killed": 1, "end not recorded": 1})

    # @feature data-store.profiler-recorder
    def test_identical_statements_running_at_once_count_as_duplicates(self):
        this_process, mine, base = process_stamp(), uuid4().hex, time.time() - 10
        runs = [("same", 0.1, 3.0), ("same", 0.5, 1.0), ("other", 0.6, 1.0), ("same", 4.0, 1.0)]
        for sql, offset, duration in runs:
            start = self.query_start(sql, base + offset, mine, **this_process)
            events.write(start)
            events.write(
                {
                    "id": start["id"],
                    "kind": "query.end",
                    "ts": start["ts"] + duration,
                    "duration": duration,
                    "ok": True,
                }
            )

        # only the second run of `same` started while the first was still running
        found = self.recorded(dashboard=mine, since=base - 1)
        self.assertEqual(found["queries"]["duplicates_in_flight"], 1)


class TestProfilerDashboard(InsightsIntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_user(OWNER, roles=["Insights User"])
        create_user(READER, roles=["Insights User"])
        with as_user(OWNER):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Profiler Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": [
                        {
                            "type": "source",
                            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
                        }
                    ],
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Profiler Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": {
                        "limit": 50,
                        "rows": [
                            {"dimension_name": "status", "column_name": "status", "data_type": "String"}
                        ],
                        "columns": [],
                        "values": [
                            {
                                "measure_name": "count",
                                "column_name": "name",
                                "aggregation": "count",
                                "data_type": "Integer",
                            }
                        ],
                        "order_by": [],
                    },
                }
            ).insert()
            cls.dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Profiler Test Dashboard",
                    "workbook": workbook.name,
                    "items": [
                        {"type": "chart", "chart": chart.name},
                        {
                            "type": "filter",
                            "filter_name": "Description",
                            "filter_type": "String",
                            "default_operator": "contains",
                            "default_value": FILTER_DEFAULT,
                            "links": {chart.name: f"`{query.name}`.`description`"},
                        },
                    ],
                }
            ).insert()

    @classmethod
    def tearDownClass(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        delete_users(OWNER, READER)
        super().tearDownClass()

    # @feature data-store.profiler-dashboard
    def test_a_dashboard_is_built_as_a_readers_load_builds_it_and_nothing_runs(self):
        logged = frappe.db.count(LOG)
        with as_user(OWNER), db_connections():
            found = targets.resolve({"dashboard": self.dashboard.name})

        self.assertEqual(frappe.db.count(LOG), logged)
        [card] = found["charts"]
        self.assertIsNone(card["error"])
        self.assertEqual([p["part"] for p in card["statements"]], ["chart", "row count"])
        # the dashboard filter's default reached both statements the card runs
        for part in card["statements"]:
            self.assertIn(FILTER_DEFAULT, events.read_sql(part["digest"]))

    # @feature data-store.profiler-dashboard
    def test_a_profile_keeps_each_scans_filters_and_names_its_date_bound(self):
        con = duckdb.connect()
        con.execute(
            """
            CREATE TABLE events AS
            SELECT i AS id, CASE WHEN i % 7 = 0 THEN 'a' ELSE 'b' END AS event_name,
                TIMESTAMP '2024-01-01' + INTERVAL (i) SECOND AS captured_at
            FROM range(200000) t(i)
            """
        )

        profile = statement.profile(
            con,
            "SELECT count(*) FROM events WHERE event_name = 'a' AND captured_at >= TIMESTAMP '2024-01-02'",
            30,
        )

        self.assertIsNone(profile["error"])
        [scan] = profile["plan"]["scans"]
        self.assertEqual(
            (scan["table"], scan["date_bounds"]),
            ("events", [{"column": "captured_at", "operator": ">=", "value": "2024-01-02 00:00:00"}]),
        )
        self.assertIn("event_name='a'", scan["filters"])

    # @feature data-store.profiler-dashboard
    def test_an_experiment_puts_the_instance_setting_back(self):
        con = duckdb.connect(config={"threads": 3})

        runs = statement.threads_sweep(con, "SELECT 42", [1, 2], 10)

        self.assertEqual([(r["threads"], r["error"]) for r in runs], [(1, None), (2, None)])
        self.assertEqual(con.execute("SELECT current_setting('threads')").fetchone()[0], 3)

    # @feature data-store.profiler-recorder data-store.profiler-dashboard
    def test_only_an_insights_admin_may_use_the_profiler(self):
        calls = {
            "start_recording": lambda: profiler_api.start_recording(5),
            "recording_report": lambda: profiler_api.recording_report(),
            "start_profile": lambda: profiler_api.start_profile(dashboard=self.dashboard.name),
            "get_statement": lambda: profiler_api.get_statement("0123456789abcdef"),
        }
        with as_user(READER):
            for name, call in calls.items():
                with self.subTest(name), self.assertRaises(frappe.PermissionError):
                    call()
