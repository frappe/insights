"""The admin API in front of the v2 migrator.

The migrator has its own suite; this one is about the surface. Who may call it,
what a caller may name, that the dry run stays dry, that the write leaves the
request, and that asking twice migrates once.

The v2 fixture goes in with SQL, the way the migrator reads it, and is built
from the same helpers the assembly suite uses.

`frappe.enqueue` does not run inline under tests: `call_directly` is
`now or (not is_async and not frappe.in_test)`, so the default `is_async=True`
puts a real job on redis, where the bench's own worker - which imports
`apps/insights`, not this worktree - dies on `ModuleNotFoundError`. So the
queueing tests patch `frappe.enqueue` and assert what it was handed, and the
job body is called directly.

To drive the queue for real, run a worker that imports the worktree:

    OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES wt run <worktree> -- worker --queue long

The environment variable is not optional on macOS. RQ forks a work-horse per
job, and CoreFoundation aborts in the child; without it every job fails with
"Work-horse terminated unexpectedly ... signal 6", which looks like a bug in
the job and is not one.
"""

import json
from unittest.mock import patch

import frappe

from insights.api.v2_migration import (
    MAX_DASHBOARDS,
    get_v2_dashboards,
    get_v2_migration_status,
    job_id_for,
    migrate_v2_dashboards,
    preview_v2_dashboard,
    run_v2_dashboard_migration,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    USER_1,
    as_user,
    create_test_user,
    delete_users,
)
from insights.tests.test_v2_workbook_assembly import (
    V2_SOURCE_TITLE,
    V2_SOURCE_V3_NAME,
    count_column,
    group_by,
    insert_row,
    v2_query,
)

DASHBOARD = "DSH-MIGAPI"
BASE = "QRY-MIGAPI-1"
STORED = "QRY-MIGAPI-2"
TITLE = "Migration API Test"
UNKNOWN = "DSH-DOES-NOT-EXIST"


class TestV2MigrationAPI(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_user(USER_1)
        cls.create_v3_data_source()
        cls.create_v2_dashboard()

    @classmethod
    def after_class(cls):
        cls.delete_v3_output()
        cls.delete_v2_fixture()
        frappe.db.delete(DT.DATA_SOURCE, {"name": V2_SOURCE_V3_NAME})
        delete_users(USER_1)

    # -- fixtures ----------------------------------------------------------

    @classmethod
    def create_v3_data_source(cls):
        if frappe.db.exists(DT.DATA_SOURCE, V2_SOURCE_V3_NAME):
            return
        frappe.get_doc(
            {
                "doctype": DT.DATA_SOURCE,
                "name": V2_SOURCE_V3_NAME,
                "title": V2_SOURCE_TITLE,
                "status": "Inactive",
                "database_type": "DuckDB",
                "database_name": "v2_migration_test",
            }
        ).db_insert()

    @classmethod
    def create_v2_dashboard(cls):
        cls.delete_v2_fixture()

        base = v2_query(BASE, "tabIssue", [group_by("status", "Status"), count_column()])
        stored = v2_query(
            STORED,
            BASE,
            [group_by("Status", "Status"), count_column("Count of records")],
            data_source="Query Store",
        )
        for row in (base, stored):
            insert_row("Insights Query", {k: v for k, v in row.items() if k != "transforms"})

        insert_row("Insights Dashboard", {"name": DASHBOARD, "title": TITLE})

        items = [
            {
                "name": 910001,
                "item_type": "Bar",
                "item_id": "910001",
                "layout": json.dumps({"i": 910001, "x": 0, "y": 0, "w": 10, "h": 8}),
                "options": json.dumps(
                    {
                        "query": STORED,
                        "title": "Issues by Status",
                        "xAxis": "Status",
                        "yAxis": ["Count of records"],
                    }
                ),
            },
            {
                "name": 910002,
                "item_type": "Text",
                "item_id": "910002",
                "layout": json.dumps({"i": 910002, "x": 0, "y": 8, "w": 20, "h": 2}),
                "options": json.dumps({"markdown": "<b>notes</b>"}),
            },
        ]
        for idx, item in enumerate(items, start=1):
            insert_row(
                "Insights Dashboard Item",
                {
                    "parent": DASHBOARD,
                    "parenttype": "Insights Dashboard",
                    "parentfield": "items",
                    "idx": idx,
                    **item,
                },
            )

    @classmethod
    def delete_v2_fixture(cls):
        frappe.db.sql("delete from `tabInsights Dashboard Item` where parent = %s", (DASHBOARD,))
        frappe.db.sql("delete from `tabInsights Dashboard` where name = %s", (DASHBOARD,))
        frappe.db.sql("delete from `tabInsights Query` where name in %(names)s", {"names": (BASE, STORED)})

    @classmethod
    def delete_v3_output(cls):
        for workbook in frappe.get_all(DT.WORKBOOK, filters={"title": TITLE}, pluck="name"):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, ignore_permissions=True)

    def setUp(self):
        super().setUp()
        self.delete_v3_output()

    # -- helpers -----------------------------------------------------------

    def v3_row_counts(self):
        return {
            doctype: frappe.db.count(doctype) for doctype in (DT.WORKBOOK, DT.QUERY, DT.CHART, DT.DASHBOARD)
        }

    def listed(self, search=TITLE):
        return {row["name"]: row for row in get_v2_dashboards(search=search)}

    # -- the list ----------------------------------------------------------

    def test_the_list_reports_what_a_migration_would_involve(self):
        row = self.listed()[DASHBOARD]
        self.assertEqual(row["title"], TITLE)
        self.assertEqual(row["item_count"], 2)
        # The text item names no query, so only the chart item counts.
        self.assertEqual(row["query_count"], 1)
        self.assertIsNone(row["migrated_workbook"])
        self.assertIsNone(row["migrated_dashboard"])

    def test_the_list_names_the_workbook_a_migrated_dashboard_landed_in(self):
        run_v2_dashboard_migration(DASHBOARD)
        row = self.listed()[DASHBOARD]
        self.assertTrue(row["migrated_workbook"])
        self.assertEqual(
            row["migrated_dashboard"],
            frappe.db.get_value(DT.DASHBOARD, {"old_name": DASHBOARD}, "name"),
        )

    def test_a_search_that_matches_nothing_returns_nothing(self):
        self.assertEqual(get_v2_dashboards(search="no dashboard is called this"), [])

    def test_a_search_term_is_a_parameter_not_a_fragment(self):
        """A quote in the term must reach the database as a value."""
        self.assertEqual(get_v2_dashboards(search="' or 1=1 -- "), [])

    # -- the preview -------------------------------------------------------

    def test_the_preview_reports_the_plan(self):
        preview = preview_v2_dashboard(DASHBOARD)
        self.assertTrue(preview["converts_cleanly"])
        self.assertEqual(preview["counts"]["queries"]["total"], 2)
        self.assertEqual(preview["counts"]["items"], {"total": 2, "converted": 2, "dropped": 0})
        self.assertIn(DASHBOARD, preview["report"])
        self.assertEqual(preview["unresolved_data_sources"], [])

    def test_the_preview_writes_nothing(self):
        before = self.v3_row_counts()
        preview_v2_dashboard(DASHBOARD)
        self.assertEqual(self.v3_row_counts(), before)
        self.assertFalse(frappe.db.exists(DT.DASHBOARD, {"old_name": DASHBOARD}))

    def test_the_preview_leaves_v2_untouched(self):
        before = frappe.db.sql("select modified from `tabInsights Dashboard` where name = %s", (DASHBOARD,))
        preview_v2_dashboard(DASHBOARD)
        after = frappe.db.sql("select modified from `tabInsights Dashboard` where name = %s", (DASHBOARD,))
        self.assertEqual(before, after)

    def test_an_unknown_dashboard_cannot_be_previewed(self):
        with self.assertRaises(frappe.ValidationError):
            preview_v2_dashboard(UNKNOWN)

    # -- queueing ----------------------------------------------------------

    def test_a_migration_is_queued_not_run_in_the_request(self):
        with patch("frappe.enqueue") as enqueue:
            result = migrate_v2_dashboards([DASHBOARD])

        self.assertEqual(result["accepted"], [DASHBOARD])
        self.assertEqual(result["skipped"], [])
        self.assertFalse(frappe.db.exists(DT.DASHBOARD, {"old_name": DASHBOARD}))

        enqueue.assert_called_once()
        _, kwargs = enqueue.call_args
        self.assertEqual(kwargs["dashboard"], DASHBOARD)
        self.assertEqual(kwargs["job_id"], job_id_for(DASHBOARD))
        self.assertTrue(kwargs["deduplicate"])
        self.assertEqual(kwargs["queue"], "long")

    def test_an_unknown_dashboard_is_skipped_with_a_reason(self):
        with patch("frappe.enqueue") as enqueue:
            result = migrate_v2_dashboards([UNKNOWN])

        enqueue.assert_not_called()
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["skipped"][0]["reason"], "not_found")

    def test_a_repeat_is_skipped_rather_than_queued_again(self):
        run_v2_dashboard_migration(DASHBOARD)
        with patch("frappe.enqueue") as enqueue:
            result = migrate_v2_dashboards([DASHBOARD])

        enqueue.assert_not_called()
        self.assertEqual(result["accepted"], [])
        skipped = result["skipped"][0]
        self.assertEqual(skipped["reason"], "already_migrated")
        self.assertTrue(skipped["workbook"])

    def test_the_same_name_twice_is_queued_once(self):
        with patch("frappe.enqueue") as enqueue:
            result = migrate_v2_dashboards([DASHBOARD, DASHBOARD])

        self.assertEqual(result["accepted"], [DASHBOARD])
        self.assertEqual(enqueue.call_count, 1)

    def test_more_than_the_bound_is_rejected(self):
        with patch("frappe.enqueue") as enqueue:
            with self.assertRaises(frappe.ValidationError):
                migrate_v2_dashboards([f"DSH-{i}" for i in range(MAX_DASHBOARDS + 1)])
        enqueue.assert_not_called()

    def test_an_empty_list_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            migrate_v2_dashboards([])

    # -- the job -----------------------------------------------------------

    def test_the_job_migrates_the_dashboard(self):
        result = run_v2_dashboard_migration(DASHBOARD)
        self.assertFalse(result["skipped"])
        self.assertEqual(
            result["dashboard"],
            frappe.db.get_value(DT.DASHBOARD, {"old_name": DASHBOARD}, "name"),
        )

    def test_running_the_job_twice_makes_one_workbook(self):
        first = run_v2_dashboard_migration(DASHBOARD)
        second = run_v2_dashboard_migration(DASHBOARD)

        self.assertTrue(second["skipped"])
        self.assertEqual(first["workbook"], second["workbook"])
        self.assertEqual(len(frappe.get_all(DT.WORKBOOK, filters={"title": TITLE})), 1)

    def test_the_job_refuses_a_name_that_is_not_a_v2_dashboard(self):
        with self.assertRaises(frappe.ValidationError):
            run_v2_dashboard_migration(UNKNOWN)

    # -- status ------------------------------------------------------------

    def test_status_is_not_started_before_anything_runs(self):
        status = get_v2_migration_status([DASHBOARD])
        self.assertEqual(status[DASHBOARD]["status"], "not_started")
        self.assertIsNone(status[DASHBOARD]["workbook"])

    def test_status_comes_from_old_name_once_it_is_migrated(self):
        run_v2_dashboard_migration(DASHBOARD)
        status = get_v2_migration_status([DASHBOARD])[DASHBOARD]
        self.assertEqual(status["status"], "migrated")
        self.assertTrue(status["workbook"])
        self.assertEqual(
            status["dashboard"],
            frappe.db.get_value(DT.DASHBOARD, {"old_name": DASHBOARD}, "name"),
        )
        self.assertIsNone(status["error"])

    def test_status_without_a_list_covers_every_v2_dashboard(self):
        run_v2_dashboard_migration(DASHBOARD)
        self.assertEqual(get_v2_migration_status()[DASHBOARD]["status"], "migrated")

    # -- permission --------------------------------------------------------

    def test_an_insights_user_reaches_none_of_it(self):
        with as_user(USER_1):
            for call in (
                lambda: get_v2_dashboards(),
                lambda: preview_v2_dashboard(DASHBOARD),
                lambda: migrate_v2_dashboards([DASHBOARD]),
                lambda: get_v2_migration_status([DASHBOARD]),
            ):
                with self.assertRaises(frappe.PermissionError):
                    call()

    def test_an_insights_user_cannot_migrate_anything(self):
        with as_user(USER_1), patch("frappe.enqueue") as enqueue:
            with self.assertRaises(frappe.PermissionError):
                migrate_v2_dashboards([DASHBOARD])
        enqueue.assert_not_called()
        self.assertFalse(frappe.db.exists(DT.DASHBOARD, {"old_name": DASHBOARD}))
