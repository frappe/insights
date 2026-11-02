import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import frappe

import insights
from insights.api.data_sources import (
    get_data_source_table,
    get_data_source_table_columns,
    get_data_source_table_row_count,
)
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    execute_warehouse_table_import,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import InsightsTablev3
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import UUID_DOCTYPE, as_user, create_uuid_doctype, delete_uuid_doctype

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

    `ToDo` has a `permission_query_conditions` hook in frappe, so it stands in for
    any doctype whose rows are restricted per user.
    """

    @classmethod
    def before_class(cls):
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

    def permitted_count(self, user):
        with self.as_user(user):
            return len(frappe.get_list("ToDo", limit_page_length=0))

    # @feature data-source.table-preview
    def test_row_count_matches_permitted_rows(self):
        for user in (USER_A, USER_B):
            with self.as_user(user):
                self.assertEqual(
                    get_data_source_table_row_count(SITE_DB, "tabToDo"),
                    self.permitted_count(user),
                )

    # @feature data-source.table-preview permissions.site-user-permissions
    def test_preview_shows_only_permitted_rows(self):
        for user in (USER_A, USER_B):
            with self.as_user(user):
                rows = get_data_source_table(SITE_DB, "tabToDo")["rows"]
                allowed = set(frappe.get_list("ToDo", pluck="name", limit_page_length=0))
                self.assertEqual({row["name"] for row in rows}, allowed)

    # @feature data-source.table-preview
    def test_column_list_survives_permission_filtering(self):
        # the row filter is a semi-join, so it must not drop columns from the preview
        with self.as_user(USER_A):
            columns = get_data_source_table_columns(SITE_DB, "tabToDo")

        self.assertTrue(any(column.column == "description" for column in columns))


class TestUUIDNameRowPermissions(InsightsIntegrationTestCase):
    """A DocType named by a MariaDB `uuid` is filtered per user, read live and from the data store."""

    TABLE = f"tab{UUID_DOCTYPE}"

    @classmethod
    def before_class(cls):
        create_user(USER_A)
        create_user(USER_B)
        create_uuid_doctype()
        for user, count in ((USER_A, 2), (USER_B, 3)):
            with as_user(user):
                for i in range(count):
                    frappe.get_doc({"doctype": UUID_DOCTYPE, "title": f"{user} #{i}"}).insert()

    @classmethod
    def after_class(cls):
        delete_uuid_doctype()
        for email in (USER_A, USER_B):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)

    def before_test(self):
        tmpdir = tempfile.mkdtemp(prefix="insights_uuid_name_test_")
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        self.enterContext(
            patch.object(insights.warehouse, "get_db_path", return_value=str(Path(tmpdir) / "store.duckdb"))
        )
        self.enterContext(patch.object(insights, "create_toast"))
        self.enterContext(patch("frappe.utils.telemetry.capture"))
        insights.db_connections.pop("insights", None)

    def assert_each_user_reads_only_their_rows(self, use_live_connection):
        for user, count in ((USER_A, 2), (USER_B, 3)):
            with self.as_user(user):
                allowed = set(frappe.get_list(UUID_DOCTYPE, pluck="name", limit_page_length=0))
                table = InsightsTablev3.get_ibis_table(
                    SITE_DB, self.TABLE, use_live_connection=use_live_connection, import_if_not_exists=False
                )
                names = {str(name) for name in table.name.execute()}

            self.assertEqual(len(allowed), count)
            self.assertEqual(names, allowed)

    # @feature permissions.site-user-permissions
    def test_a_uuid_named_table_shows_each_user_only_the_rows_they_may_read(self):
        self.assert_each_user_reads_only_their_rows(use_live_connection=True)

        execute_warehouse_table_import(SITE_DB, self.TABLE)
        self.assert_each_user_reads_only_their_rows(use_live_connection=False)
