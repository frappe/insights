"""A grant of access reports the object, who received it and how many.

`share_granted` is one event for every way access is given: a workbook to a
user or to the organization, a dashboard published, a team granted resources.
The funnel reads sharing without knowing which dialog was used.
"""

from unittest.mock import patch

import frappe

from insights.api.workbooks import update_share_permissions
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
    delete_workbooks,
)

OWNER = "share_granted_owner@test.com"
VIEWER = "share_granted_viewer@test.com"
WORKBOOK_TITLE = "Share Granted Test Workbook"


class TestShareGranted(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_user(OWNER, first_name="Share", last_name="Owner", roles=["Insights User", "Insights Admin"])
        create_user(VIEWER, first_name="Share", last_name="Viewer", roles="Insights User")

    @classmethod
    def after_class(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        delete_users(OWNER, VIEWER)

    def before_test(self):
        self.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE)

    def after_test(self):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)

    def granted(self, action):
        """Return the `share_granted` properties each capture carried."""
        with patch("insights.telemetry.capture") as sender:
            action()
        return [call.kwargs for call in sender.call_args_list if call.args == ("share_granted",)]

    # @feature telemetry.share-granted
    def test_a_workbook_shared_with_users_counts_them(self):
        def share():
            with self.as_user(OWNER):
                update_share_permissions(
                    self.workbook.name,
                    [{"user": VIEWER, "read": 1, "write": 0}],
                )

        self.assertEqual(
            self.granted(share),
            [{"object": "workbook", "with": "user", "count": 1}],
        )

    # @feature telemetry.share-granted
    def test_a_workbook_already_shared_grants_nothing(self):
        def share():
            with self.as_user(OWNER):
                update_share_permissions(
                    self.workbook.name,
                    [{"user": VIEWER, "read": 1, "write": 0}],
                )

        share()
        self.assertEqual(self.granted(share), [])

    # @feature telemetry.share-granted
    def test_a_workbook_opened_to_the_organization_grants_once(self):
        def share():
            with self.as_user(OWNER):
                update_share_permissions(self.workbook.name, [], organization_access="view")

        self.assertEqual(
            self.granted(share),
            [{"object": "workbook", "with": "org", "count": 1}],
        )

    # @feature telemetry.share-granted
    def test_a_dashboard_made_public_grants_the_public(self):
        dashboard = create_test_dashboard(OWNER, self.workbook.name)

        def publish():
            with self.as_user(OWNER):
                doc = frappe.get_doc(DT.DASHBOARD, dashboard.name)
                doc.visibility = "Public"
                doc.save()

        self.assertEqual(
            self.granted(publish),
            [{"object": "dashboard", "with": "public", "count": 1}],
        )

    # @feature telemetry.share-granted
    def test_a_publish_the_save_refuses_grants_nothing(self):
        query = create_test_query(OWNER, self.workbook.name)
        chart = create_test_chart(OWNER, self.workbook.name, query=query.name)
        dashboard = create_test_dashboard(OWNER, self.workbook.name, chart=chart.name)

        def publish():
            with self.as_user(OWNER):
                doc = frappe.get_doc(DT.DASHBOARD, dashboard.name)
                doc.visibility = "Public"
                with self.assertRaises(frappe.ValidationError):
                    doc.save()

        self.assertEqual(self.granted(publish), [])

    # @feature telemetry.share-granted
    def test_a_team_grant_names_the_resource_type(self):
        team = frappe.get_doc({"doctype": DT.TEAM, "team_name": "Share Granted Team"}).insert()
        self.addCleanup(frappe.delete_doc, DT.TEAM, team.name, force=True)

        def grant():
            team.append(
                "team_permissions",
                {"resource_type": DT.DATA_SOURCE, "resource_name": "Site DB"},
            )
            team.save()

        self.assertEqual(
            self.granted(grant),
            [{"object": "data_source", "with": "team", "count": 1}],
        )
