import unittest

import frappe


class TestInsightsPermissions(unittest.TestCase):
    def setUp(self):
        create_test_users()
        create_test_data_sources()
        create_test_tables()
        create_test_teams()

    def tearDown(self):
        delete_test_teams()
        delete_test_tables()
        delete_test_data_sources()
        delete_test_users()

    def toggle_team_permissions(self, enable):
        frappe.db.set_value(
            "Insights Settings", None, "enable_team_permissions", enable
        )

    def test_permissions_for_non_insights_user(self):
        # check if a non insights user can access a insights doctypes
        pass

    def test_permissions_on_team_based_doctype_with_team_permissions_disabled(self):
        self.toggle_team_permissions(False)
        # check if a insights user can access all teams
        pass

    def test_permission_on_team_based_doctype_with_team_permissions_enabled(self):
        self.toggle_team_permissions(True)
        # check if insights user can access a team, table, data source
        # add user to a team, give access to a table, data source
        # check if insights user can access a team, table, data source
        pass

    def test_permission_for_admin_on_team_based_doctype_with_team_permissions_enabled(
        self,
    ):
        self.toggle_team_permissions(True)
        # check if admin can access all teams, tables, data sources
        pass

    def test_permission_for_workbook(self):
        # check if insights user has access to no workbooks
        # check if insights user can create a workbook
        # check if insights user can share a workbook
        # check if another insights user can access a shared workbook
        # unshare the workbook and check if another insights user can access it
        pass

    def test_permission_for_dashboard(self):
        # check if insights user has access to no dashboard
        # create a workbook
        # check if insights user can create a dashboard
        # check if insights user can share a dashboard
        # check if another insights user can access the shared dashboard
        # unshare the dashboard and check if another insights user can access it
        # share the workbook with read access
        # check if another insights user can access the workbook dashboard
        # check if another user cannot create a dashboard for the workbook
        pass

    def test_permission_for_chart(self):
        # check if insights user has access to no chart
        # create a workbook
        # create a chart
        # check if insights user can share a chart
        # check if another insights user can access the shared chart
        # unshare the chart and check if another insights user can access it
        # share the workbook with read access
        # check if another insights user can access the workbook chart
        # check if another user cannot create a chart for the workbook
        # unshare the workbook and chart
        # create a dashboard and add a chart
        # share the dashboard
        # check if another insights user can access the dashboard chart
        pass

    def test_permission_for_query(self):
        # check if insights user has access to no query
        # create a workbook
        # create a query
        # share the workbook with read access
        # check if another insights user can access the workbook query
        # check if another user cannot create a query for the workbook
        # unshare the workbook and query
        # create a chart and select the query
        # share the chart
        # check if another insights user can access the chart query & data_query
        # unshare the chart
        # create a dashboard and add a chart
        # share the dashboard
        # check if another insights user can access the dashboard chart query & data_query

        # drilldown cases
        # if a non-insights user creates a query, it should fail, because role permissions will not allow it
        # if an insights user creates a query against a workbook, then it should check workbook permissions
        # if an insights user creates a query without a workbook, then it should check permissions of the sources
        pass


def create_test_users():
    # create a website user
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": "web_user@test.com",
            "first_name": "Web",
            "last_name": "User",
            "send_welcome_email": 0,
            "user_type": "Website User",
            "enabled": 1,
        }
    ).insert()

    # create a non insights user
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": "non_insights_user@test.com",
            "first_name": "Non",
            "last_name": "Insights User",
            "send_welcome_email": 0,
            "user_type": "System User",
            "enabled": 1,
        }
    ).insert()

    # create a insights user
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": "insights_user1@test.com",
            "first_name": "Insights",
            "last_name": "User",
            "send_welcome_email": 0,
            "user_type": "System User",
            "enabled": 1,
        }
    ).insert()
    user.add_roles("Insights User")

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": "insights_user2@test.com",
            "first_name": "Insights",
            "last_name": "User",
            "send_welcome_email": 0,
            "user_type": "System User",
            "enabled": 1,
        }
    ).insert()
    user.add_roles("Insights User")

    # create a insights admin
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": "insights_admin@test.com",
            "first_name": "Insights",
            "last_name": "Admin",
            "send_welcome_email": 0,
            "user_type": "System User",
            "enabled": 1,
        }
    ).insert()
    user.add_roles("Insights Admin")


def delete_test_users():
    frappe.delete_doc("User", "web_user@test.com", force=True)
    frappe.delete_doc("User", "non_insights_user@test.com", force=True)
    frappe.delete_doc("User", "insights_user1@test.com", force=True)
    frappe.delete_doc("User", "insights_user2@test.com", force=True)
    frappe.delete_doc("User", "insights_admin@test.com", force=True)


def create_test_data_sources():
    frappe.get_doc(
        {
            "doctype": "Insights Data Source v3",
            "database_type": "DuckDB",
            "database_name": "Test DuckDB",
        }
    ).insert()


def delete_test_data_sources():
    frappe.delete_doc("Insights Data Source v3", "Test DuckDB", force=True)


def create_test_tables():
    frappe.get_doc(
        {
            "doctype": "Insights Table v3",
            "table_name": "table1",
            "data_source": "Test DuckDB",
        }
    ).insert()

    frappe.get_doc(
        {
            "doctype": "Insights Table v3",
            "table_name": "table2",
            "data_source": "Test DuckDB",
        }
    ).insert()

    frappe.get_doc(
        {
            "doctype": "Insights Table v3",
            "table_name": "table3",
            "data_source": "Test DuckDB",
        }
    ).insert()


def delete_test_tables():
    frappe.delete_doc("Insights Table v3", "table1", force=True)
    frappe.delete_doc("Insights Table v3", "table2", force=True)
    frappe.delete_doc("Insights Table v3", "table3", force=True)


def create_test_teams():
    team1 = frappe.get_doc({"doctype": "Insights Team", "team_name": "team1"})
    team1.append("team_members", {"user": "insights_user1@test.com"})
    team1.save()


def delete_test_teams():
    frappe.delete_doc("Insights Team", "team1", force=True)
