"""Which user's rows a link published before `visibility` keeps serving.

See `insights/patches/run_public_charts_as_owner.py`. Before, the publishing
document stored its publisher in `permission_user`, and a public read filtered
rows by that user. The `run_as_owner` Check can only name the chart's owner.

These tests cover a site without the `permission_user` column, as on an upgrade
from a v3 release before v3.13. Adding or dropping a column is DDL, and DDL
commits, which breaks the savepoints this suite runs inside. So the tests cannot
cover a stored publisher, and they patch `has_column` instead of dropping it.
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

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_another_person_published_keeps_running_as_its_reader(self):
        """Checking Run as owner would show guests the chart owner's rows, but the
        link served the dashboard owner's rows. So the card refuses to load, and
        the chart's owner decides in the chart's share dialog."""
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

        self.assertTrue(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_another_person_published_with_a_script_keeps_running_as_its_reader(self):
        """A script reads anything its running user can, so the rows depend on the user."""
        self.published_by_another_person_on(
            [*EXTERNAL_TABLE, {"type": "code", "code": "results = frappe.get_list('ToDo')"}]
        )

        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))

    # @feature shared.chart-on-public-dashboard permissions.chart-run-as-owner
    def test_a_link_whose_owner_cannot_read_its_table_keeps_running_as_its_reader(self):
        """The owner would get no rows. A later grant to the owner would then show
        the table to guests, and nobody would have decided that."""
        with patch(
            "insights.insights.doctype.insights_team.insights_team.check_table_permission",
            side_effect=lambda data_source, table, user=None, raise_error=True: user == PUBLISHER,
        ):
            self.published_by_another_person_on(EXTERNAL_TABLE)

        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "run_as_owner"))
