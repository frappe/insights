"""What an admin may do to a team, and what the Admin team refuses.

`update_team` rewrites a team whole: the name, the roster and the grants all come
from the request, so what the request leaves out is removed. The Admin team is the
exception at both ends — it keeps its name, and it cannot be deleted.
"""

import frappe

from insights.api.user import create_team, delete_team, update_team
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_user, delete_users
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
        with self.as_user(ADMIN):
            update_team(
                {
                    "name": "Admin",
                    "team_name": "Renamed Admins",
                    "team_members": [{"user": member} for member in members_of("Admin")],
                    "team_permissions": [],
                }
            )

        self.assertTrue(frappe.db.exists(DT.TEAM, "Admin"))
        self.assertFalse(frappe.db.exists(DT.TEAM, "Renamed Admins"))

        with self.as_user(ADMIN), self.assertRaises(frappe.ValidationError):
            delete_team("Admin")

        self.assertTrue(frappe.db.exists(DT.TEAM, "Admin"))

    # @feature settings.team-manage
    def test_a_deleted_admin_leaves_the_admin_team_so_the_next_admin_joins_it(self):
        departed = create_user("departed_admin@test.com", roles="Insights Admin").name
        self.assertIn(departed, members_of("Admin"))

        delete_users(departed)
        self.assertNotIn(departed, members_of("Admin"))

        newcomer = create_user("next_admin@test.com", roles="Insights Admin").name
        self.addCleanup(delete_users, newcomer)
        self.assertIn(newcomer, members_of("Admin"))


class TestTableRestrictionValidation(InsightsIntegrationTestCase):
    SAVEPOINT = "test_table_restriction_validation"

    def team_restricting(self, restriction):
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

        table = get_table_name("Site DB", "tabToDo")
        if not frappe.db.exists(DT.TABLE, table):
            frappe.get_doc(
                {"doctype": DT.TABLE, "table": "tabToDo", "label": "ToDo", "data_source": "Site DB"}
            ).insert(ignore_permissions=True)
        columns = [{"name": "status", "type": "String"}, {"name": "priority", "type": "String"}]
        frappe.db.set_value(DT.TABLE, table, "columns", frappe.as_json(columns), update_modified=False)
        team = frappe.get_doc({"doctype": DT.TEAM, "team_name": TEAM_NAME})
        team.append(
            "team_permissions",
            {"resource_type": DT.TABLE, "resource_name": table, "table_restrictions": restriction},
        )
        return team

    # @feature settings.team-manage
    def test_a_restriction_that_is_not_a_condition_on_the_tables_columns_is_refused(self):
        for restriction in ('_.status == "Open"', 'state == "Open"', "status", "status =="):
            with self.subTest(restriction=restriction):
                with self.assertRaisesRegex(frappe.ValidationError, "is not a condition on its columns"):
                    self.team_restricting(restriction).insert(ignore_permissions=True)

    # @feature settings.team-manage
    def test_a_condition_on_the_tables_columns_is_saved(self):
        team = self.team_restricting('(status == "Open") | (priority == "High")').insert(
            ignore_permissions=True
        )

        self.assertTrue(frappe.db.exists(DT.TEAM, team.name))
