"""An Insights user is a desk user.

Frappe signs in OAuth clients, such as frappectl, and serves its MCP endpoint
only to users with the Desk User role, which it gives only to System Users. A
migrate re-imports `insights/fixtures/role.json`, so the role's desk access
there is what every site ends with, whatever an admin set by hand.
"""

import frappe
from frappe.utils.fixtures import sync_fixtures

from insights.insights.doctype.insights_user_invitation.test_insights_user_invitation import (
    make_invitation,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import create_user, delete_users

INSIGHTS_ONLY = "desk_access_insights_only@test.com"
NO_INSIGHTS_ROLE = "desk_access_no_insights_role@test.com"
INVITEE = "desk_access_invitee@test.com"


class TestInsightsUserIsADeskUser(InsightsIntegrationTestCase):
    def tearDown(self):
        delete_users(INSIGHTS_ONLY, NO_INSIGHTS_ROLE, INVITEE)
        frappe.db.delete("Insights User Invitation", {"email": INVITEE})
        sync_fixtures("insights")

    # @feature settings.desk-access
    def test_a_migrate_makes_a_user_with_only_insights_user_a_desk_user_and_keeps_them_one(self):
        # a site before the upgrade, where the role had no desk access
        frappe.db.set_value("Role", "Insights User", "desk_access", 0)
        create_user(INSIGHTS_ONLY, roles="Insights User", user_type="Website User")
        create_user(NO_INSIGHTS_ROLE, user_type="Website User")
        self.assertEqual(frappe.db.get_value("User", INSIGHTS_ONLY, "user_type"), "Website User")

        sync_fixtures("insights")
        self.assert_desk_user(INSIGHTS_ONLY)
        self.assertEqual(frappe.db.get_value("User", NO_INSIGHTS_ROLE, "user_type"), "Website User")

        sync_fixtures("insights")
        self.assert_desk_user(INSIGHTS_ONLY)

    # @feature settings.desk-access
    def test_an_invitee_who_accepts_is_a_desk_user(self):
        sync_fixtures("insights")
        make_invitation(INVITEE).accept()
        self.assert_desk_user(INVITEE)

    def assert_desk_user(self, user):
        self.assertEqual(frappe.db.get_value("User", user, "user_type"), "System User")
        frappe.clear_cache(user=user)
        self.assertIn("Desk User", frappe.get_roles(user))
