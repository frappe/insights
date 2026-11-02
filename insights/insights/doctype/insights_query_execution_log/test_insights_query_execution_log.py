# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import subprocess
import sys

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

import insights
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import connect_duckdb
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    UNUSED_TABLE_DAYS,
    WAREHOUSE_DB_NAME,
)
from insights.insights.doctype.insights_data_source_v3.ibis_utils import execute_ibis_query
from insights.insights.doctype.insights_query_execution_log.insights_query_execution_log import (
    InsightsQueryExecutionLog,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import create_test_query, create_test_workbook
from insights.utils import log_failed_execution

# An import job in another process holds the store this way while it commits.
HOLD_WRITE_LOCK = """
import sys, duckdb
con = duckdb.connect(sys.argv[1], read_only=False)
print("held", flush=True)
sys.stdin.read()
con.close()
"""


class TestInsightsQueryExecutionLog(FrappeTestCase):
    def setUp(self):
        frappe.db.delete("Insights Query Execution Log")

    def create_log(self, days_ago):
        doc = frappe.get_doc({"doctype": "Insights Query Execution Log", "sql": "select 1"}).insert()
        creation = add_days(now_datetime(), -days_ago)
        frappe.db.set_value(doc.doctype, doc.name, "creation", creation, update_modified=False)
        return doc.name

    # @feature data-store.execution-log-retention
    def test_clears_logs_older_than_retention(self):
        old = self.create_log(20)
        recent = self.create_log(5)

        InsightsQueryExecutionLog.clear_old_logs(10)

        self.assertFalse(frappe.db.exists("Insights Query Execution Log", old))
        self.assertTrue(frappe.db.exists("Insights Query Execution Log", recent))

    # @feature data-store.execution-log-retention
    def test_default_retention_covers_data_store_cleanup_window(self):
        retention = frappe.get_hooks("default_log_clearing_doctypes")["Insights Query Execution Log"][-1]
        self.assertGreater(retention, UNUSED_TABLE_DAYS)


class TestExecutionLogOutcomes(InsightsIntegrationTestCase):
    SAVEPOINT = "test_execution_log_outcomes"

    def before_test(self):
        self.reference = f"Execution Log Test {frappe.generate_hash(length=8)}"
        self.addCleanup(frappe.db.delete, "Insights Query Execution Log", {"query": self.reference})

    def logs(self, *fields):
        return frappe.get_all(
            "Insights Query Execution Log",
            filters={"query": self.reference},
            fields=fields,
            order_by="creation asc, name asc",
        )

    def run_sql(self, sql, **kwargs):
        db = connect_duckdb()
        self.addCleanup(db.disconnect)
        return execute_ibis_query(db.sql(sql), reference_name=self.reference, **kwargs)

    # @feature data-store.execution-log-failures
    def test_a_failed_run_is_kept_with_its_error_after_the_request_rolls_back(self):
        with self.assertRaises(Exception) as failed:
            self.run_sql("select cast('not a number' as integer) as n")

        frappe.db.rollback(save_point=self.SAVEPOINT)  # as the failed request does

        [log] = self.logs("status", "error_type", "error", "sql")
        self.assertEqual(
            (log.status, log.error_type, log.error),
            ("Failed", type(failed.exception).__name__, str(failed.exception)),
        )
        self.assertIn("not a number", log.sql)

    # @feature data-store.execution-log-failures
    def test_a_run_the_concurrency_limit_turned_away_is_not_kept(self):
        # the run never started, and the client retries it on the 503
        with self.assertRaises(frappe.ServiceUnavailableError):
            with log_failed_execution(query_name=self.reference):
                raise frappe.ServiceUnavailableError("Server is busy. Please try again in a few seconds.")

        self.assertEqual(self.logs("status"), [])

    # @feature data-store.execution-log-failures
    def test_a_data_store_read_a_writer_holds_the_file_against_is_kept_as_locked(self):
        workbook = create_test_workbook("Administrator")
        query = create_test_query("Administrator", workbook.name)
        query.db_set("use_live_connection", 0)
        self.reference = query.name
        self.addCleanup(frappe.db.delete, "Insights Query Execution Log", {"query": self.reference})

        if reader := insights.db_connections.pop(WAREHOUSE_DB_NAME, None):
            reader.disconnect()
        writer = subprocess.Popen(
            [sys.executable, "-c", HOLD_WRITE_LOCK, insights.warehouse.get_db_path()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(writer.stdout.readline().strip(), "held")
            with self.assertRaises(Exception):
                query.execute()
        finally:
            writer.communicate()

        [log] = self.logs("status", "error_type", "error", "data_store")
        self.assertEqual((log.status, log.error_type, log.data_store), ("Locked", "IOException", 1))
        self.assertIn("Could not set lock", log.error)

    # @feature data-store.execution-log-cache
    def test_each_run_records_whether_its_answer_came_from_the_result_cache(self):
        sql = f"select '{frappe.generate_hash()}' as a"

        self.run_sql(sql, cache=False)
        self.run_sql(sql)
        _result, time_taken = self.run_sql(sql)
        self.run_sql(sql, force=True)

        self.assertEqual(time_taken, -1, "the third run did not read the cache")
        self.assertEqual(
            [(log.status, log.cache) for log in self.logs("status", "cache")],
            [("Success", "Off"), ("Success", "Miss"), ("Success", "Forced")],
            "a cache hit ran nothing, so it writes no row",
        )
