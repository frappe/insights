"""Opening a workbook or viewing a dashboard reports where the view came from.

The value is the reader's surface and arrives from the frontend. The server
keeps it to the list `docs/telemetry.md` names. A Guest on a public link names
none, and is the one reader whose default is `shared`.
"""

from unittest.mock import patch

import frappe

from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_dashboard,
    create_test_workbook,
    create_user,
    delete_users,
    delete_workbooks,
)

OWNER = "daily_activity_owner@test.com"


class TestDailyActivity(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_user(OWNER, first_name="Daily", last_name="Owner", roles="Insights Admin")
        cls.workbook = create_test_workbook(OWNER, title="Daily Activity Workbook").name
        cls.dashboard = create_test_dashboard(OWNER, cls.workbook, title="Daily Activity Dashboard").name

    @classmethod
    def after_class(cls):
        delete_workbooks(title_prefix="Daily Activity Workbook")
        delete_users(OWNER)

    def sent(self, doctype, name, **args):
        """Return the properties of the daily event this view reported."""
        with patch("frappe.utils.telemetry.capture") as sender:
            frappe.get_doc(doctype, name).track_view(**args)
        return {
            call.args[0]: (call.kwargs["interval"], call.kwargs["properties"])
            for call in sender.call_args_list
        }

    # @feature telemetry.daily-activity
    def test_a_workbook_opened_from_a_recents_entry_reports_the_recents_entry(self):
        with self.as_user(OWNER):
            events = self.sent(DT.WORKBOOK, self.workbook, via="recent")

        interval, properties = events["workbook_opened"]
        self.assertEqual(interval, "1d")
        self.assertEqual(properties["via"], "recent")

    # @feature telemetry.daily-activity
    def test_a_workbook_opened_by_an_unnamed_route_reports_a_link(self):
        """The value comes from the frontend, so anything off the list is a link."""
        with self.as_user(OWNER):
            events = self.sent(DT.WORKBOOK, self.workbook, via="sidebar")

        self.assertEqual(events["workbook_opened"][1]["via"], "link")

    # @feature telemetry.daily-activity
    def test_a_guest_viewing_a_dashboard_reports_the_shared_surface_and_is_logged(self):
        with self.as_user("Guest"):
            events = self.sent(DT.DASHBOARD, self.dashboard)

        interval, properties = events["dashboard_viewed"]
        self.assertEqual(interval, "1d")
        self.assertEqual(properties["surface"], "shared")
        self.assertTrue(
            frappe.db.exists(
                "View Log",
                {
                    "reference_doctype": DT.DASHBOARD,
                    "reference_name": self.dashboard,
                    "viewed_by": "Guest",
                },
            )
        )
