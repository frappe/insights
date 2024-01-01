# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from insights.api.dashboards import get_dashboard_list
from insights.api.data_sources import get_data_sources, get_table_columns, get_tables
from insights.api.queries import get_queries

from .insights_team_client import get_teams


class TestInsightsTeam(FrappeTestCase):
    def setUp(self):
        frappe.db.set_single_value("Insights Settings", "enable_permissions", 1)

    def tearDown(self):
        frappe.db.set_single_value("Insights Settings", "enable_permissions", 0)

    def test_get_teams(self):
        # case 0: check error if not allowed to read insights team
        user = self.make_new_user("abc@example.com")
        frappe.set_user(user.name)
        self.assertRaises(frappe.PermissionError, get_teams)
        user.add_roles("Insights User")
        self.assertRaises(frappe.PermissionError, get_teams)
        user.add_roles("Insights Admin")
        get_teams()

        # case 1: no teams
        teams = get_teams()
        self.assertEqual(teams, [])

        # case 2: one team with no members
        team = frappe.get_doc({"doctype": "Insights Team", "team_name": "Team 1"})
        team.append("team_members", {"user": "Administrator"})
        team.save()

        teams = get_teams()
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0]["team_name"], "Team 1")
        self.assertEqual(len(teams[0]["members"]), 1)
        self.assertEqual(teams[0]["source_count"], 0)
        self.assertEqual(teams[0]["table_count"], 0)
        self.assertEqual(teams[0]["query_count"], 0)
        self.assertEqual(teams[0]["dashboard_count"], 0)

        # case 3: allow one data source with one table
        frappe.get_doc(
            {
                "doctype": "Insights Data Source",
                "title": "Test Get Teams",
                "database_name": "test_get_teams",
                "database_type": "SQLite",
            }
        ).save()
        frappe.get_doc(
            {
                "doctype": "Insights Table",
                "label": "Demo Table",
                "table": "tabDemo Table",
                "data_source": "Test Get Teams",
            }
        ).db_insert()
        team.append(
            "team_permissions",
            {
                "resource_type": "Insights Data Source",
                "resource_name": "Test Get Teams",
            },
        )
        team.save()

        teams = get_teams()
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0]["team_name"], "Team 1")
        self.assertEqual(len(teams[0]["members"]), 1)
        self.assertEqual(teams[0]["source_count"], 1)
        self.assertEqual(teams[0]["table_count"], 1)

        # case 4: give access to one query and add one insights user to team
        query = frappe.get_doc(
            {
                "doctype": "Insights Query",
                "title": "Test Get Teams Query",
                "data_source": "Test Get Teams",
            }
        ).save()

        team.append("team_members", {"user": user.name})
        team.team_permissions = []
        team.append(
            "team_permissions",
            {"resource_type": "Insights Query", "resource_name": query.name},
        )
        team.save()
        user.remove_roles("Insights Admin")
        user.remove_roles("Insights User")

        self.assertRaises(frappe.PermissionError, get_data_sources)
        self.assertRaises(frappe.PermissionError, get_table_columns)
        self.assertRaises(frappe.PermissionError, get_tables)
        self.assertRaises(frappe.PermissionError, get_queries)
        self.assertRaises(frappe.PermissionError, get_dashboard_list)

        user.add_roles("Insights User")
        self.assertEqual(get_data_sources(), [])
        self.assertRaises(
            frappe.PermissionError, get_table_columns, "Test Get Teams", "Demo Table"
        )
        self.assertRaises(frappe.PermissionError, get_tables, "Test Get Teams")
        self.assertEqual(get_queries()[0]["name"], query.name)

    def make_new_user(self, email, insights_role=None):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "user_type": "Website User",
                "email": email,
                "send_welcome_email": 0,
                "first_name": email.split("@")[0],
            }
        ).insert(ignore_permissions=True)
        if insights_role:
            user.add_roles(insights_role)
        return user
