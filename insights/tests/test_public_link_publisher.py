"""Which user's rows a link published before `visibility` keeps serving.

See `insights/patches/run_public_charts_as_owner.py`. Before, the publishing
document stored its publisher in `permission_user`, and a public read filtered
rows by that user. The `run_as_owner` Check can only name the chart's owner.

Where the publisher was another user, the publisher becomes the owner.

These tests cover a site without the `permission_user` column, as on an upgrade
from a v3 release before v3.13. Adding or dropping a column is DDL, and DDL
commits, which breaks the savepoints this suite runs inside. So the tests cannot
cover a stored publisher, and they patch `has_column` instead of dropping it.
"""

from unittest.mock import patch

import frappe

from insights.patches.run_public_charts_as_owner import execute as run_public_charts_as_owner
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
)
from insights.upgrade import ITEM

EXTERNAL_TABLE = [
    {
        "type": "source",
        "table": {"type": "table", "data_source": "Public Link Source", "table_name": "orders"},
    }
]
OWNER = "Administrator"
PREFIX = "Public Link Test"
PUBLISHER = "public_link_publisher@test.com"
PREVIOUS_OWNER = "public_link_previous_owner@test.com"


class TestPublicLinkPublisher(InsightsIntegrationTestCase):
    SAVEPOINT = "test_public_link_publisher"

    def before_test(self):
        frappe.db.delete(ITEM)

    @classmethod
    def before_class(cls):
        workbook = create_test_workbook(OWNER, title=PREFIX)
        query = create_test_query(OWNER, workbook.name, title=f"{PREFIX} Query")
        cls.query = query.name
        cls.chart = create_test_chart(OWNER, workbook.name, query.name, title=f"{PREFIX} Chart").name
        cls.dashboard = create_test_dashboard(
            OWNER, workbook.name, cls.chart, title=f"{PREFIX} Dashboard"
        ).name
        cls.workbook = workbook.name
        create_user(PUBLISHER, first_name="Public", last_name="Publisher", roles="Insights User")
        create_user(PREVIOUS_OWNER, first_name="Previous", last_name="Owner", roles="Insights User")

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(PUBLISHER, PREVIOUS_OWNER)

    # the state earlier patches leave a published dashboard in
    def published(self):
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "visibility", "Public")
        frappe.db.set_value(DT.CHART, self.chart, "run_as_owner", 0)

    def run_patch_without_the_column(self):
        with patch.object(frappe.db, "has_column", return_value=False):
            run_public_charts_as_owner()

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_published_before_the_publisher_was_recorded_runs_as_its_owner(self):
        """The backfill that added `permission_user` filled it with the publishing
        document's owner, so the link served that user's rows."""
        self.published()

        self.run_patch_without_the_column()

        self.assertTrue(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))

    # @feature upgrade.public-links-keep-rows
    def test_a_link_on_rows_desk_filters_per_reader_tells_its_owner_readers_see_the_owners_rows(self):
        """A signed-in reader saw their own ToDo rows in Insights before v3.50, and sees the
        owner's once the chart runs as its owner."""
        self.published()

        self.run_patch_without_the_column()

        message, data = frappe.db.get_value(
            ITEM, {"code": "P10", "reference_name": self.chart}, ["message", "data"]
        )
        self.assertIn("reads ToDo", message)
        self.assertEqual(
            frappe.parse_json(data),
            {"chart": f"{PREFIX} Chart", "owner": OWNER, "reason": "site_table", "table": "ToDo"},
        )

    # @feature upgrade.public-links-keep-rows
    def test_a_link_on_rows_every_reader_reads_alike_is_not_reported(self):
        self.published_by_another_person_on(EXTERNAL_TABLE)

        self.assertFalse(frappe.db.exists(ITEM, {"code": "P10"}))

    def assert_moved_to_the_publisher(self):
        self.assertEqual(frappe.db.get_value(DT.CHART, self.chart, "owner"), PUBLISHER)
        self.assertTrue(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))
        # readers see the rows they saw, and the previous owner keeps edit, so
        # nobody has anything to act on
        self.assertFalse(frappe.db.exists(ITEM, {"code": "P11", "reference_name": self.chart}))

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner upgrade.public-links-keep-rows
    def test_a_link_another_person_published_moves_to_the_publisher(self):
        """The link served the dashboard owner's rows, and Run as owner can only
        name the chart's owner. So the publisher becomes the owner."""
        self.published()
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "owner", PUBLISHER)

        self.run_patch_without_the_column()

        self.assert_moved_to_the_publisher()

    # @feature upgrade.public-links-keep-rows
    def test_a_link_a_disabled_user_published_keeps_running_as_its_reader(self):
        self.published()
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "owner", PUBLISHER)
        frappe.db.set_value(DT.USER, PUBLISHER, "enabled", 0)

        self.run_patch_without_the_column()

        self.assertEqual(frappe.db.get_value(DT.CHART, self.chart, "owner"), OWNER)
        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))
        message, data = frappe.db.get_value(
            ITEM, {"code": "P11", "reference_name": self.chart}, ["message", "data"]
        )
        self.assertIn(f"{PUBLISHER}, who published it, is disabled", message)
        self.assertEqual(
            frappe.parse_json(data),
            {"chart": f"{PREFIX} Chart", "publisher": PUBLISHER, "publisher_disabled": True},
        )

    def published_by_another_person_on(self, operations):
        """Publishes the chart on a dashboard another user owns, with `operations` as its query."""
        frappe.db.set_value(DT.QUERY, self.query, "operations", frappe.as_json(operations))
        self.published()
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "owner", PUBLISHER)
        frappe.db.set_single_value("Insights Settings", "enable_permissions", 0)

        with (
            patch(
                "insights.insights.doctype.insights_table_v3.insights_table_v3.is_site_db", return_value=False
            ),
            patch("insights.insights.doctype.insights_team.insights_team.is_site_db", return_value=False),
        ):
            self.run_patch_without_the_column()

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_another_person_published_on_rows_everyone_reads_runs_as_its_owner(self):
        """No Table Restriction applies to this external table, so the owner and
        the publisher read the same rows. Run as owner serves guests the same
        rows as before."""
        self.published_by_another_person_on(EXTERNAL_TABLE)

        self.assertEqual(frappe.db.get_value(DT.CHART, self.chart, "owner"), OWNER)
        self.assertTrue(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner upgrade.public-links-keep-rows
    def test_a_link_another_person_published_with_a_script_moves_to_the_publisher(self):
        """A script reads anything its running user can, so the rows depend on the user."""
        self.published_by_another_person_on(
            [*EXTERNAL_TABLE, {"type": "code", "code": "results = frappe.get_list('ToDo')"}]
        )

        self.assert_moved_to_the_publisher()

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner upgrade.public-links-keep-rows
    def test_a_link_whose_owner_cannot_read_its_table_moves_to_the_publisher(self):
        """The owner would get no rows, and the publisher got the rows the link served."""
        with patch(
            "insights.insights.doctype.insights_team.insights_team.check_table_permission",
            side_effect=lambda data_source, table, user=None, raise_error=True: user == PUBLISHER,
        ):
            self.published_by_another_person_on(EXTERNAL_TABLE)

        self.assert_moved_to_the_publisher()

    # @feature upgrade.public-links-keep-rows
    def test_a_dashboard_row_naming_a_deleted_chart_is_skipped(self):
        """Insights before v3.50 left such a row after a forced delete. It reaches no chart."""
        self.published()
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "owner", PUBLISHER)
        frappe.get_doc(
            {
                "doctype": "Insights Dashboard Chart v3",
                "parenttype": DT.DASHBOARD,
                "parent": self.dashboard,
                "parentfield": "linked_charts",
                "chart": "deleted-chart",
            }
        ).db_insert()

        self.run_patch_without_the_column()

        self.assert_moved_to_the_publisher()

    # @feature upgrade.public-links-keep-rows upgrade.owners-keep-access
    def test_the_previous_owner_of_a_moved_chart_can_still_edit_it(self):
        """The workbook share patch shares a workbook with the owners of its
        members, and the chart no longer names its previous owner."""
        frappe.db.set_value(DT.CHART, self.chart, "owner", PREVIOUS_OWNER, update_modified=False)
        self.published()
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "owner", PUBLISHER)

        self.run_patch_without_the_column()

        self.assertEqual(frappe.db.get_value(DT.CHART, self.chart, "owner"), PUBLISHER)
        self.assertTrue(frappe.has_permission(DT.WORKBOOK, "write", doc=self.workbook, user=PREVIOUS_OWNER))

    def published_on_a_table_only_admins_read(self, chart_owner: str, publisher: str):
        """Publishes the chart, owned by `chart_owner`, on `publisher`'s dashboard,
        with a query on Role, which an Insights User may not read in desk."""
        operations = [
            {"type": "source", "table": {"type": "table", "data_source": "Site DB", "table_name": "tabRole"}}
        ]
        frappe.db.set_value(DT.QUERY, self.query, "operations", frappe.as_json(operations))
        frappe.db.set_value(DT.CHART, self.chart, "owner", chart_owner, update_modified=False)
        self.published()
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "owner", publisher)

        self.run_patch_without_the_column()

    # @feature upgrade.public-links-keep-rows
    def test_a_link_whose_owner_cannot_read_its_table_tells_its_owner_readers_see_not_permitted(self):
        """The chart runs as its owner, and desk does not let the owner read Role."""
        self.published_on_a_table_only_admins_read(PREVIOUS_OWNER, PREVIOUS_OWNER)

        message, data = frappe.db.get_value(
            ITEM, {"code": "P10", "reference_name": self.chart}, ["message", "data"]
        )
        self.assertIn("can't read Role", message)
        self.assertEqual(
            frappe.parse_json(data),
            {
                "chart": f"{PREFIX} Chart",
                "owner": PREVIOUS_OWNER,
                "reason": "unreadable",
                "doctypes": ["Role"],
            },
        )

    # @feature upgrade.public-links-keep-rows
    def test_a_link_moved_to_a_publisher_who_cannot_read_its_table_says_readers_see_not_permitted(self):
        self.published_on_a_table_only_admins_read(OWNER, PUBLISHER)

        self.assertEqual(frappe.db.get_value(DT.CHART, self.chart, "owner"), PUBLISHER)
        items = frappe.get_all(
            ITEM, filters={"code": "P11", "reference_name": self.chart}, fields=["message", "data"]
        )
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertIn("can't read Role", item.message)
            self.assertEqual(frappe.parse_json(item.data)["doctypes"], ["Role"])
        # the publisher's note can't give them a role, so the admins are asked too
        data = frappe.db.get_value(ITEM, {"code": "P10", "reference_name": self.chart}, "data")
        self.assertEqual(
            frappe.parse_json(data),
            {"chart": f"{PREFIX} Chart", "owner": PUBLISHER, "reason": "unreadable", "doctypes": ["Role"]},
        )
