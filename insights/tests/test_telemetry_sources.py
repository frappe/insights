"""What connecting a source and importing a table report, and what they keep.

A connection test and an import are the two things that fail where the site
owner can see it and the maintainers cannot. Both report the kind of source and
how it ended. The host, the account, the driver's words and the query all stay
here, and every size is a bucket.
"""

from unittest.mock import MagicMock, patch

import frappe

import insights
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    WAREHOUSE_DB_NAME,
    WarehouseTable,
    WarehouseTableImporter,
)
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.telemetry import duration_bucket, rows_bucket
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT

SECRET = "hunter2"
DRIVER_ERROR = OSError(f'connection to "postgresql://svc:{SECRET}@warehouse.internal" failed')


def sent(sender):
    """The properties one capture sent, without the ones every event sends."""
    _, kwargs = sender.call_args
    return {k: v for k, v in kwargs["properties"].items() if k not in ("app_version", "entry")}


class TestBuckets(InsightsIntegrationTestCase):
    # @feature telemetry.source-outcomes
    def test_a_row_count_falls_in_the_bucket_that_holds_its_lower_bound(self):
        self.assertEqual(rows_bucket(0), "under_10k")
        self.assertEqual(rows_bucket(9_999), "under_10k")
        self.assertEqual(rows_bucket(10_000), "10k_to_100k")
        self.assertEqual(rows_bucket(99_999), "10k_to_100k")
        self.assertEqual(rows_bucket(100_000), "100k_to_1m")
        self.assertEqual(rows_bucket(999_999), "100k_to_1m")
        self.assertEqual(rows_bucket(1_000_000), "over_1m")

    # @feature telemetry.source-outcomes
    def test_a_duration_falls_in_the_bucket_that_holds_its_lower_bound(self):
        self.assertEqual(duration_bucket(0), "under_1s")
        self.assertEqual(duration_bucket(0.9), "under_1s")
        self.assertEqual(duration_bucket(1), "1_to_5s")
        self.assertEqual(duration_bucket(4.9), "1_to_5s")
        self.assertEqual(duration_bucket(5), "5_to_30s")
        self.assertEqual(duration_bucket(29.9), "5_to_30s")
        self.assertEqual(duration_bucket(30), "over_30s")


class TestDataSourceEvents(InsightsIntegrationTestCase):
    TITLE = "Telemetry Source Events"

    @classmethod
    def after_class(cls):
        for name in frappe.get_all(DT.DATA_SOURCE, {"title": cls.TITLE}, pluck="name"):
            frappe.delete_doc(DT.DATA_SOURCE, name, force=True, ignore_permissions=True)

    def create_source(self, **fields):
        with patch("frappe.utils.telemetry.capture") as sender:
            doc = frappe.get_doc(
                {
                    "doctype": DT.DATA_SOURCE,
                    "title": self.TITLE,
                    "database_type": "DuckDB",
                    "database_name": "telemetry_source_events",
                    **fields,
                }
            ).insert()
        self.addCleanup(frappe.delete_doc, DT.DATA_SOURCE, doc.name, force=True, ignore_permissions=True)
        return sender

    # @feature telemetry.source-outcomes
    def test_a_new_source_reports_its_kind_and_whether_it_is_encrypted(self):
        sender = self.create_source()
        created = next(call for call in sender.call_args_list if call.args[0] == "data_source_created")
        own = {k: v for k, v in created.kwargs["properties"].items() if k not in ("app_version", "entry")}
        self.assertEqual(own, {"type": "duckdb", "ssl": False})

    # @feature telemetry.source-outcomes
    def test_a_connection_that_answers_is_reported_as_ok(self):
        with patch("frappe.utils.telemetry.capture") as sender, db_connections():
            self.assertTrue(frappe.get_doc(DT.DATA_SOURCE, "Site DB").test_connection())

        self.assertEqual(sender.call_args.args, ("data_source_tested", "insights"))
        self.assertEqual(sent(sender), {"type": "site_db", "ok": True})

    def refused_test(self):
        """Test a source the driver refuses, and return the call it sent."""
        doc = frappe.get_doc(DT.DATA_SOURCE, "Site DB")
        insights.db_connections.pop(doc.name, None)
        with patch("frappe.utils.telemetry.capture") as sender, db_connections():
            with patch.object(doc, "_get_db_connection", side_effect=DRIVER_ERROR):
                self.assertIsNone(doc.test_connection())
        return sender

    # @feature telemetry.source-outcomes
    def test_a_connection_the_driver_refuses_is_reported_with_its_kind(self):
        self.assertEqual(
            sent(self.refused_test()),
            {"type": "site_db", "ok": False, "error_kind": "connection"},
        )

    # @feature telemetry.source-outcomes
    def test_a_refused_connection_names_neither_the_host_nor_the_account(self):
        report = frappe.as_json(self.refused_test().call_args.kwargs["properties"])
        for detail in (SECRET, "warehouse.internal", "svc", "postgresql://"):
            self.assertNotIn(detail, report)


class TestImportOutcome(InsightsIntegrationTestCase):
    """What an import reports once it reaches a terminal state.

    The remote read is the boundary, and a stand-in answers it. Everything the
    event sends comes off the log the run itself writes.
    """

    DATA_SOURCE = "Site DB"
    TABLE = "telemetry_import_outcome_table"
    RESUMED_TABLE = "telemetry_import_resumed_table"
    ROW_LIMIT = 100

    @classmethod
    def before_class(cls):
        cls.table_docs = []
        for table, fields in (
            (cls.TABLE, {"sync_mode": "Full", "row_limit": cls.ROW_LIMIT}),
            (
                cls.RESUMED_TABLE,
                {
                    "sync_mode": "Incremental",
                    "sync_cursor_column": "modified",
                    "last_sync_bookmark": "2026-01-01 00:00:00",
                },
            ),
        ):
            doc = frappe.get_doc(
                {
                    "doctype": DT.TABLE,
                    "table": table,
                    "label": table,
                    "data_source": cls.DATA_SOURCE,
                    **fields,
                }
            )
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True)
            cls.table_docs.append(doc.name)

    @classmethod
    def after_class(cls):
        for name in cls.table_docs:
            frappe.delete_doc(DT.TABLE, name, force=True, ignore_permissions=True)

    def run_import(self, table=None, rows=0, failure=None, prepare=None):
        """Run an import whose remote read is stood in for, and return the call it sent."""
        importer = WarehouseTableImporter(WarehouseTable(self.DATA_SOURCE, table or self.TABLE))

        def batch_import():
            if failure:
                raise failure
            importer.log.rows_imported = rows
            importer.log.status = "Completed"

        with (
            patch("frappe.utils.telemetry.capture") as sender,
            patch.object(insights, "create_toast"),
            patch.object(
                importer,
                "prepare_remote_table",
                side_effect=(lambda: prepare(importer)) if prepare else None,
            ),
            patch.object(importer, "start_batch_import", side_effect=batch_import),
        ):
            if failure:
                with self.assertRaises(type(failure)):
                    importer.start_import()
            else:
                importer.start_import()

        frappe.delete_doc("Insights Table Import Log", importer.log.name, force=True, ignore_permissions=True)
        return sent(sender)

    # @feature telemetry.source-outcomes
    def test_a_finished_import_reports_its_size_as_a_bucket(self):
        self.assertEqual(
            self.run_import(rows=42),
            {
                "outcome": "ok",
                "hit_row_limit": False,
                "rows_bucket": "under_10k",
                "duration_bucket": "under_1s",
                "resumed": False,
            },
        )

    # @feature telemetry.source-outcomes
    def test_an_import_that_copied_as_many_rows_as_it_may_reports_the_cap(self):
        self.assertTrue(self.run_import(rows=self.ROW_LIMIT)["hit_row_limit"])

    # @feature telemetry.source-outcomes
    def test_an_import_that_raises_is_reported_as_failed(self):
        report = self.run_import(failure=ValueError("the remote table went away"))
        self.assertEqual(report["outcome"], "failed")
        self.assertEqual(report["rows_bucket"], "under_10k")
        self.assertNotIn("went away", frappe.as_json(report))

    # @feature telemetry.source-outcomes
    def test_an_incremental_import_that_starts_from_a_bookmark_is_reported_as_resumed(self):
        stored_table = MagicMock()

        def resolve(importer):
            with patch.dict(insights.db_connections, {WAREHOUSE_DB_NAME: stored_table}):
                importer._resolve_incremental_bookmark()

        self.assertEqual(
            self.run_import(table=self.RESUMED_TABLE, rows=42, prepare=resolve),
            {
                "outcome": "ok",
                "hit_row_limit": False,
                "rows_bucket": "under_10k",
                "duration_bucket": "under_1s",
                "resumed": True,
            },
        )
