import frappe
import frappe.share

from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.tests.factories import DT, create_user, delete_doc_if_exists, delete_users, delete_workbooks

WEB_USER_EMAIL = "web_user@test.com"
NON_INSIGHTS_USER = "non_insights_user@test.com"
USER_1 = "insights_user1@test.com"
USER_2 = "insights_user2@test.com"
ADMIN = "insights_admin@test.com"

TEST_DS_TITLE = "Test DuckDB"
TEST_DS = frappe.scrub(TEST_DS_TITLE)
TEST_TABLE1 = get_table_name(TEST_DS, "table1")
TEST_TABLE2_NAME = get_table_name(TEST_DS, "table2")
TEST_TABLE3_NAME = get_table_name(TEST_DS, "table3")


def create_test_users():
    create_user(
        WEB_USER_EMAIL,
        first_name="Web",
        last_name="User",
        user_type="Website User",
    )
    create_user(
        NON_INSIGHTS_USER,
        first_name="Non",
        last_name="Insights User",
    )
    create_user(
        USER_1,
        first_name="Insights",
        last_name="User",
        roles="Insights User",
    )
    create_user(
        USER_2,
        first_name="Insights",
        last_name="User",
        roles="Insights User",
    )
    create_user(
        ADMIN,
        first_name="Insights",
        last_name="Admin",
        roles="Insights Admin",
    )


def delete_test_users():
    delete_users(
        WEB_USER_EMAIL,
        NON_INSIGHTS_USER,
        USER_1,
        USER_2,
        ADMIN,
    )


def create_test_data_sources():
    frappe.get_doc(
        {
            "doctype": DT.DATA_SOURCE,
            "title": TEST_DS_TITLE,
            "database_type": "DuckDB",
            "database_name": "test_duckdb",
        }
    ).insert()


def delete_test_data_sources():
    delete_doc_if_exists(DT.DATA_SOURCE, TEST_DS)


def create_test_tables():
    for table_name in ("table1", "table2", "table3"):
        frappe.get_doc(
            {
                "doctype": DT.TABLE,
                "table": table_name,
                "label": table_name,
                "data_source": TEST_DS,
                "sync_mode": "Full",
            }
        ).insert()


def delete_test_tables():
    delete_doc_if_exists(DT.TABLE, TEST_TABLE1)
    delete_doc_if_exists(DT.TABLE, TEST_TABLE2_NAME)
    delete_doc_if_exists(DT.TABLE, TEST_TABLE3_NAME)


def create_test_teams():
    team = frappe.get_doc({"doctype": DT.TEAM, "team_name": "team1"})
    team.append("team_members", {"user": USER_1})
    team.save()
    clear_team_cache()
    return team


def delete_test_teams():
    delete_doc_if_exists(DT.TEAM, "team1")


def update_dashboard_access(dashboard_name, people_with_access):
    frappe.get_doc(DT.DASHBOARD, dashboard_name).update_access(
        {
            "is_public": 0,
            "is_shared_with_organization": 0,
            "people_with_access": people_with_access,
        }
    )


def share_chart(chart_name, user):
    frappe.share.add(DT.CHART, chart_name, user=user, read=1, notify=0)


def unshare_chart(chart_name, user):
    share_name = frappe.db.get_value(
        "DocShare",
        {
            "share_doctype": DT.CHART,
            "share_name": chart_name,
            "user": user,
        },
    )
    if share_name:
        frappe.delete_doc("DocShare", share_name, ignore_permissions=True)


def delete_test_workbooks():
    delete_workbooks(owners=[USER_1, USER_2, ADMIN])


def cleanup_test_fixtures():
    delete_test_workbooks()
    delete_test_teams()
    delete_test_tables()
    delete_test_data_sources()
    delete_test_users()
    clear_team_cache()
