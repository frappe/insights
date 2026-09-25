"""Whose rows a link published before `visibility` keeps serving.

See `insights/patches/run_public_charts_as_owner.py`. The base recorded the
publisher on the document that published the content and filtered a public read
by that person; the Check this branch reads instead can only name the owner.

What a test on a migrated bench can reach: a site that never had the base's
`permission_user` column, the one a v3 release before v3.13 upgrades from.
Adding or dropping the column is a DDL, which commits, so the arm that reads a
recorded publisher cannot be exercised here without breaking every savepoint
this suite runs inside, and the column's absence is stated rather than made.
"""

from contextlib import redirect_stdout
from io import StringIO
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

EXTERNAL_TABLE = [
    {
        "type": "source",
        "table": {"type": "table", "data_source": "Public Rung Source", "table_name": "orders"},
    }
]
OWNER = "Administrator"
PREFIX = "Public Rung Test"
PUBLISHER = "public_rung_publisher@test.com"


class TestPublicLinkPublisher(InsightsIntegrationTestCase):
    SAVEPOINT = "test_public_link_publisher"

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

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(PUBLISHER)

    # the migrated shape, written the way the earlier patches write it
    def published(self):
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "visibility", "Public")
        frappe.db.set_value(DT.CHART, self.chart, "run_as_owner", 0)

    def run_patch_without_the_column(self):
        with patch.object(frappe.db, "has_column", return_value=False):
            run_public_charts_as_owner()

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_published_before_the_publisher_was_recorded_runs_as_its_owner(self):
        """The base's own backfill wrote the publishing document's owner into the
        column it added, and the link served that person's rows."""
        self.published()

        self.run_patch_without_the_column()

        self.assertTrue(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_another_person_published_keeps_running_as_its_reader(self):
        """Checking the box would hand the guest the chart owner's rows, and the
        base was serving the dashboard owner's. The card refuses instead, and the
        owner decides from the chart's own share dialog."""
        self.published()
        frappe.db.set_value(DT.DASHBOARD, self.dashboard, "owner", PUBLISHER)

        with redirect_stdout(StringIO()) as output:
            self.run_patch_without_the_column()

        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))
        self.assertIn(
            f'{self.chart} "{PREFIX} Chart": owner {OWNER}, published by {PUBLISHER}: reads the site table',
            output.getvalue(),
        )

    def published_by_another_person_on(self, operations):
        """The chart, published by a dashboard someone else owns, reading `operations`."""
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
        """External data no Table Restriction narrows: the owner's rows are the
        publisher's, so checking the box serves the guest what the base did."""
        self.published_by_another_person_on(EXTERNAL_TABLE)

        self.assertTrue(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_another_person_published_with_a_script_keeps_running_as_its_reader(self):
        """A script reads whatever its running user may, so its rows are that user's."""
        self.published_by_another_person_on(
            [*EXTERNAL_TABLE, {"type": "code", "code": "results = frappe.get_list('ToDo')"}]
        )

        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_whose_owner_cannot_read_its_table_keeps_running_as_its_reader(self):
        """The owner's rows would be none of the publisher's, and a later grant to
        the owner would start serving them to guests without anyone deciding to."""
        with patch(
            "insights.insights.doctype.insights_team.insights_team.check_table_permission",
            side_effect=lambda data_source, table, user=None, raise_error=True: user == PUBLISHER,
        ):
            self.published_by_another_person_on(EXTERNAL_TABLE)

        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))
