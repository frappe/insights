# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import ibis

from insights.insights.doctype.insights_query_v3 import snapshots
from insights.tests.base import InsightsIntegrationTestCase

SOURCE_OP = {
    "type": "code",
    "code": (
        "results = [" "{'item': 'A', 'qty': 10}," "{'item': 'B', 'qty': 20}," "{'item': 'C', 'qty': 30}]"
    ),
}


class TestQuerySnapshots(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.workbook = frappe.get_doc(
            {"doctype": "Insights Workbook", "title": "Snapshot Test Workbook"}
        ).insert()

    @classmethod
    def after_class(cls):
        frappe.delete_doc("Insights Workbook", cls.workbook.name, force=True, ignore_permissions=True)

    def make_query(self, operations=None, materialized=True):
        doc = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "Snapshot Query",
                "use_live_connection": 0,
                "is_builder_query": 1,
                "is_materialized": 1 if materialized else 0,
                "snapshot_refresh_frequency": "Daily",
                "operations": frappe.as_json(operations or [SOURCE_OP]),
            }
        ).insert()
        self.addCleanup(self._cleanup_query, doc.name)
        return doc

    def _cleanup_query(self, name):
        snapshots.drop_snapshot(name)
        if frappe.db.exists("Insights Query v3", name):
            frappe.delete_doc("Insights Query v3", name, force=True, ignore_permissions=True)

    def test_refresh_builds_snapshot_and_serves_from_it(self):
        doc = self.make_query()
        snapshots.refresh_snapshot(doc.name)
        doc.reload()

        self.assertTrue(snapshots.snapshot_exists(doc.name))
        self.assertEqual(doc.snapshot_status, "Completed")
        self.assertEqual(doc.snapshot_row_count, 3)
        self.assertTrue(doc.snapshot_last_refreshed_at)

        sql = ibis.to_sql(doc.build())
        self.assertIn("query_snapshots", sql)

        rows = doc.execute(page_size=100)["rows"]
        self.assertEqual({r["item"] for r in rows}, {"A", "B", "C"})

    def test_preview_bypasses_snapshot(self):
        doc = self.make_query()
        snapshots.refresh_snapshot(doc.name)
        # previewing an intermediate operation must build live, not read the snapshot
        sql = ibis.to_sql(doc.build(active_operation_idx=0))
        self.assertNotIn("query_snapshots", sql)

    def test_non_materialized_query_never_reads_snapshot(self):
        doc = self.make_query(materialized=False)
        sql = ibis.to_sql(doc.build())
        self.assertNotIn("query_snapshots", sql)

    def test_failed_refresh_keeps_previous_snapshot(self):
        doc = self.make_query()
        snapshots.refresh_snapshot(doc.name)
        self.assertTrue(snapshots.snapshot_exists(doc.name))

        import insights.insights.doctype.insights_data_source_v3.ibis_utils as iu

        original = iu.execute_ibis_query
        iu.execute_ibis_query = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            with self.assertRaises(RuntimeError):
                snapshots.refresh_snapshot(doc.name)
        finally:
            iu.execute_ibis_query = original

        doc.reload()
        self.assertEqual(doc.snapshot_status, "Failed")
        self.assertTrue(doc.snapshot_error)
        # the old snapshot must survive and still serve the read path
        self.assertTrue(snapshots.snapshot_exists(doc.name))
        self.assertIn("query_snapshots", ibis.to_sql(doc.build()))

    def test_toggle_off_drops_snapshot(self):
        doc = self.make_query()
        snapshots.refresh_snapshot(doc.name)
        self.assertTrue(snapshots.snapshot_exists(doc.name))

        doc.is_materialized = 0
        doc.save()
        self.assertFalse(snapshots.snapshot_exists(doc.name))
        self.assertNotIn("query_snapshots", ibis.to_sql(doc.build()))

    def test_adhoc_filter_applies_on_snapshot(self):
        from insights.insights.doctype.insights_query_v3.insights_query_v3 import set_adhoc_filters

        doc = self.make_query()
        snapshots.refresh_snapshot(doc.name)

        adhoc = {
            doc.name: {
                "type": "filter_group",
                "logical_operator": "And",
                "filters": [
                    {"column": {"type": "column", "column_name": "item"}, "operator": "=", "value": "A"}
                ],
            }
        }
        with set_adhoc_filters(adhoc):
            sql = ibis.to_sql(doc.build())
            rows = doc.execute(page_size=100)["rows"]

        self.assertIn("query_snapshots", sql)
        self.assertEqual([r["item"] for r in rows], ["A"])

    def test_refresh_rejects_oversized_result(self):
        doc = self.make_query()
        original = snapshots.MAX_SNAPSHOT_ROWS
        snapshots.MAX_SNAPSHOT_ROWS = 1
        try:
            with self.assertRaises(snapshots.SnapshotTooLargeError):
                snapshots.refresh_snapshot(doc.name)
        finally:
            snapshots.MAX_SNAPSHOT_ROWS = original
        doc.reload()
        self.assertEqual(doc.snapshot_status, "Failed")

    def test_only_admin_can_toggle_materialization(self):
        from insights.tests.factories import create_user

        non_admin = create_user("snapshot-nonadmin@example.com", roles=["Insights User"])
        doc = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "Perm Test",
                "is_materialized": 1,
                "operations": frappe.as_json([SOURCE_OP]),
            }
        )
        with self.as_user(non_admin.name):
            with self.assertRaises(frappe.PermissionError):
                doc._validate_materialization_is_admin_only()
        # an admin (Administrator, restored after the context) is allowed
        doc._validate_materialization_is_admin_only()

    def test_snapshot_table_name_is_docname_verbatim(self):
        # docnames are already unique; scrubbing would fold distinct names
        # (hyphen vs underscore) onto the same snapshot table.
        self.assertEqual(snapshots.snapshot_table_name("abc-DEF_123"), "abc-DEF_123")

    def test_scheduler_due_logic(self):
        from frappe.utils import add_to_date, now_datetime

        now = now_datetime()
        due = lambda freq, last: snapshots._is_snapshot_due(
            frappe._dict(snapshot_refresh_frequency=freq, snapshot_last_refreshed_at=last), now
        )
        self.assertTrue(due("Daily", None))
        self.assertTrue(due("Daily", add_to_date(now, hours=-25)))
        self.assertFalse(due("Daily", add_to_date(now, hours=-2)))
        self.assertTrue(due("Hourly", add_to_date(now, minutes=-90)))
        self.assertFalse(due("Hourly", add_to_date(now, minutes=-10)))
