"""Guards frappe/insights#1193 — see insights/patches/name_workbooks_as_strings.py for
why `Insights Workbook` now names itself as a string instead of via `autoincrement`.
"""

import frappe

from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, USER_1, create_test_user, create_test_workbook, delete_users
from insights.tests.workbook_utils import cleanup_test_workbooks


class TestWorkbookNaming(InsightsIntegrationTestCase):
    COMMIT_AFTER_TEST_SETUP = True
    COMMIT_AFTER_TEST_TEARDOWN = True

    @classmethod
    def before_class(cls):
        cleanup_test_workbooks(USER_1)
        delete_users(USER_1)
        create_test_user(USER_1)

    @classmethod
    def after_class(cls):
        cleanup_test_workbooks(USER_1)
        delete_users(USER_1)

    def after_test(self):
        cleanup_test_workbooks(USER_1)

    def test_name_column_is_varchar(self):
        # the migration this doctype went through; an unmigrated site fails here first.
        # mariadb reports "varchar(140)", postgres "character varying"
        column_type = str(frappe.db.get_column_type(DT.WORKBOOK, "name")).lower()
        self.assertIn("char", column_type, f"expected a varchar name column, got {column_type!r}")

    def test_workbook_is_named_with_a_number_as_a_string(self):
        workbook = create_test_workbook(USER_1)

        self.assertIsInstance(workbook.name, str)
        self.assertTrue(workbook.name.isdigit(), f"expected a plain number, got {workbook.name!r}")

    def test_names_keep_counting_up(self):
        first = create_test_workbook(USER_1, title="Naming Test One")
        second = create_test_workbook(USER_1, title="Naming Test Two")

        self.assertEqual(int(second.name), int(first.name) + 1)

    def test_children_are_found_without_casting_the_name(self):
        workbook = create_test_workbook(USER_1)
        folder = frappe.get_doc(
            {
                "doctype": "Insights Folder",
                "workbook": workbook.name,
                "title": "Naming Test Folder",
                "type": "query",
            }
        ).insert()

        # the link column and the name are both varchar now, so this needs no cast on
        # either side — which is the whole point of the migration
        self.assertEqual(
            frappe.get_all("Insights Folder", filters={"workbook": workbook.name}, pluck="name"),
            [folder.name],
        )
        self.assertEqual(folder.workbook, workbook.name)
