import frappe

from insights.api.data_sources import (
    get_data_source_table,
    get_data_source_table_columns,
    get_data_source_table_row_count,
)
from insights.tests.base import InsightsIntegrationTestCase

SITE_DB = "Site DB"
USER_A = "row-perm-a@example.com"
USER_B = "row-perm-b@example.com"


def create_user(email):
    if frappe.db.exists("User", email):
        return
    user = frappe.new_doc("User")
    user.email = email
    user.first_name = email.split("@")[0]
    user.send_welcome_email = 0
    user.append("roles", {"role": "Insights User"})
    user.insert(ignore_permissions=True)


class TestSiteDBRowPermissions(InsightsIntegrationTestCase):
    """Data source exploration must not show rows the user cannot read.

    `ToDo` carries a `permission_query_conditions` hook in frappe, so it stands in for
    any doctype whose rows are restricted per user.
    """

    @classmethod
    def before_class(cls):
        cls.settings_was = frappe.db.get_single_value("Insights Settings", "apply_user_permissions")
        frappe.db.set_single_value("Insights Settings", "apply_user_permissions", 1)

        create_user(USER_A)
        create_user(USER_B)

        cls.todos = {}
        for user, count in ((USER_A, 2), (USER_B, 3)):
            cls.todos[user] = [
                frappe.get_doc(
                    {
                        "doctype": "ToDo",
                        "description": f"row perm test for {user} #{i}",
                        "allocated_to": user,
                    }
                )
                .insert(ignore_permissions=True)
                .name
                for i in range(count)
            ]

    @classmethod
    def after_class(cls):
        for names in cls.todos.values():
            for name in names:
                frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)
        for email in (USER_A, USER_B):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.set_single_value("Insights Settings", "apply_user_permissions", cls.settings_was)

    def permitted_count(self, user):
        with self.as_user(user):
            return len(frappe.get_list("ToDo", limit_page_length=0))

    def test_row_count_matches_permitted_rows(self):
        for user in (USER_A, USER_B):
            with self.as_user(user):
                self.assertEqual(
                    get_data_source_table_row_count(SITE_DB, "tabToDo"),
                    self.permitted_count(user),
                )

    def test_preview_shows_only_permitted_rows(self):
        for user in (USER_A, USER_B):
            with self.as_user(user):
                rows = get_data_source_table(SITE_DB, "tabToDo")["rows"]
                allowed = set(frappe.get_list("ToDo", pluck="name", limit_page_length=0))
                self.assertEqual({row["name"] for row in rows}, allowed)

    def test_column_list_survives_permission_filtering(self):
        # the row filter is a semi-join, so it must not drop columns from the preview
        with self.as_user(USER_A):
            columns = get_data_source_table_columns(SITE_DB, "tabToDo")

        self.assertTrue(any(column.column == "description" for column in columns))
