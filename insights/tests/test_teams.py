"""What an admin may do to a team, and what the Admin team refuses.

`update_team` rewrites a team whole: the name, the roster and the grants all come
from the request, so what the request leaves out is removed. The Admin team is the
exception at both ends — it keeps its name, and it cannot be deleted.
"""

import frappe

from insights.api.user import create_team, delete_team, update_team
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, delete_users
from insights.tests.permissions_utils import (
    ADMIN,
    USER_1,
    USER_2,
    create_test_users,
)

TEAM_NAME = "Team Test Squad"
RENAMED = "Team Test Renamed Squad"


def members_of(team_name):
    return sorted(member.user for member in frappe.get_doc(DT.TEAM, team_name).team_members)


class TestTeamManagement(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_users()

    @classmethod
    def after_class(cls):
        for team_name in (TEAM_NAME, RENAMED):
            if frappe.db.exists(DT.TEAM, team_name):
                frappe.delete_doc(DT.TEAM, team_name, force=True, ignore_permissions=True)
        delete_users(USER_1, USER_2, ADMIN)

    def make_team(self):
        with self.as_user(ADMIN):
            create_team(TEAM_NAME)
        self.addCleanup(self.drop_team)

    def drop_team(self):
        for team_name in (TEAM_NAME, RENAMED):
            if frappe.db.exists(DT.TEAM, team_name):
                frappe.delete_doc(DT.TEAM, team_name, force=True, ignore_permissions=True)

    # @feature settings.team-manage
    def test_an_admin_renames_a_team_and_rewrites_its_members(self):
        self.make_team()

        with self.as_user(ADMIN):
            update_team(
                {
                    "name": TEAM_NAME,
                    "team_name": RENAMED,
                    "team_members": [{"user": USER_1}, {"user": USER_2}],
                    "team_permissions": [],
                }
            )

        self.assertFalse(frappe.db.exists(DT.TEAM, TEAM_NAME))
        self.assertEqual(members_of(RENAMED), sorted([USER_1, USER_2]))

        # the roster is rewritten from the request, so a member left out is removed
        with self.as_user(ADMIN):
            update_team(
                {
                    "name": RENAMED,
                    "team_name": RENAMED,
                    "team_members": [{"user": USER_2}],
                    "team_permissions": [],
                }
            )

        self.assertEqual(members_of(RENAMED), [USER_2])

    # @feature settings.team-manage
    def test_the_admin_team_keeps_its_name_and_cannot_be_deleted(self):
        # the site's Admin team can carry rows for users another suite deleted, and
        # a save would fail on the dangling link before it reached the name guard
        admins = [
            member.user
            for member in frappe.get_doc(DT.TEAM, "Admin").team_members
            if frappe.db.exists("User", member.user)
        ]
        self.assertTrue(admins, "the Admin team must hold a member that still exists")

        with self.as_user(ADMIN):
            update_team(
                {
                    "name": "Admin",
                    "team_name": "Renamed Admins",
                    "team_members": [{"user": member} for member in admins],
                    "team_permissions": [],
                }
            )

        self.assertTrue(frappe.db.exists(DT.TEAM, "Admin"))
        self.assertFalse(frappe.db.exists(DT.TEAM, "Renamed Admins"))

        with self.as_user(ADMIN), self.assertRaises(frappe.ValidationError):
            delete_team("Admin")

        self.assertTrue(frappe.db.exists(DT.TEAM, "Admin"))
