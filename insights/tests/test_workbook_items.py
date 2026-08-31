"""A workbook's ordering reaches the workbook's own items.

`update_sort_orders` writes straight to the row, so the permission query that
scopes reading a query, a chart or a folder never sees the write. Write access is
held on the workbook, and the item named in the request is what says whether that
access covers it.
"""

import frappe

from insights.api.workbooks import create_folder, update_sort_orders
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
    create_test_query,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import USER_1, USER_2, create_test_users

OWNER = USER_1
OTHER = USER_2


class OrderingReachesOwnItemsOnly:
    """The rules. Both `enable_permissions` settings run them."""

    ENABLE_PERMISSIONS = 0

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.owner_workbook = create_test_workbook(OWNER, title="Sorting Owner Workbook").name
        cls.owner_query = create_test_query(OWNER, cls.owner_workbook, title="Sorting Owner Query").name
        cls.owner_chart = create_test_chart(OWNER, cls.owner_workbook, title="Sorting Owner Chart").name
        with as_user(OWNER):
            cls.owner_folder = create_folder(cls.owner_workbook, "Owner Folder", "query")

        cls.other_workbook = create_test_workbook(OTHER, title="Sorting Other Workbook").name
        cls.other_query = create_test_query(OTHER, cls.other_workbook, title="Sorting Other Query").name
        with as_user(OTHER):
            cls.other_folder = create_folder(cls.other_workbook, "Other Folder", "query")

    @classmethod
    def after_class(cls):
        for name in (cls.owner_workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)

    def sort_order_of(self, doctype, name):
        return frappe.db.get_value(doctype, name, "sort_order")

    def test_a_workbook_owner_orders_their_own_items(self):
        """The baseline the refusals below are measured against."""
        with self.as_user(OTHER):
            update_sort_orders(
                self.other_workbook,
                [
                    {"type": "query", "name": self.other_query, "sort_order": 7},
                    {"type": "folder", "name": self.other_folder, "sort_order": 3},
                ],
            )
        self.assertEqual(self.sort_order_of(DT.QUERY, self.other_query), 7)
        self.assertEqual(self.sort_order_of("Insights Folder", self.other_folder), 3)

    def test_an_item_can_be_moved_into_a_folder_of_the_same_workbook(self):
        with self.as_user(OTHER):
            update_sort_orders(
                self.other_workbook,
                [
                    {
                        "type": "query",
                        "name": self.other_query,
                        "sort_order": 1,
                        "folder": self.other_folder,
                    }
                ],
            )
        self.assertEqual(frappe.db.get_value(DT.QUERY, self.other_query, "folder"), self.other_folder)

    def test_a_query_in_another_workbook_is_not_reordered(self):
        before = self.sort_order_of(DT.QUERY, self.owner_query)
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            update_sort_orders(
                self.other_workbook,
                [{"type": "query", "name": self.owner_query, "sort_order": 99}],
            )
        self.assertEqual(self.sort_order_of(DT.QUERY, self.owner_query), before)

    def test_a_chart_in_another_workbook_is_not_reordered(self):
        before = self.sort_order_of(DT.CHART, self.owner_chart)
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            update_sort_orders(
                self.other_workbook,
                [{"type": "chart", "name": self.owner_chart, "sort_order": 99}],
            )
        self.assertEqual(self.sort_order_of(DT.CHART, self.owner_chart), before)

    def test_a_folder_in_another_workbook_is_not_reordered(self):
        before = self.sort_order_of("Insights Folder", self.owner_folder)
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            update_sort_orders(
                self.other_workbook,
                [{"type": "folder", "name": self.owner_folder, "sort_order": 99}],
            )
        self.assertEqual(self.sort_order_of("Insights Folder", self.owner_folder), before)

    def test_an_item_is_not_moved_into_a_folder_of_another_workbook(self):
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            update_sort_orders(
                self.other_workbook,
                [
                    {
                        "type": "query",
                        "name": self.other_query,
                        "sort_order": 1,
                        "folder": self.owner_folder,
                    }
                ],
            )
        self.assertNotEqual(frappe.db.get_value(DT.QUERY, self.other_query, "folder"), self.owner_folder)

    def test_a_malformed_item_is_refused_with_a_message(self):
        """A missing key used to raise KeyError, so one bad entry was a 500."""
        with self.as_user(OWNER), self.assertRaises(frappe.ValidationError):
            update_sort_orders(self.owner_workbook, [{"name": self.owner_query, "type": "query"}])

        with self.as_user(OWNER), self.assertRaises(frappe.ValidationError):
            update_sort_orders(self.owner_workbook, [{"name": self.owner_query, "sort_order": 0}])

    def test_a_filter_set_is_not_an_item_name(self):
        """One name is one document. A filter set would reach every row it
        matches, in any workbook."""
        before = self.sort_order_of(DT.QUERY, self.owner_query)
        with self.as_user(OTHER), self.assertRaises(frappe.ValidationError):
            update_sort_orders(
                self.other_workbook,
                [
                    {
                        "type": "query",
                        "name": {"title": "Sorting Owner Query"},
                        "sort_order": 99,
                    }
                ],
            )
        self.assertEqual(self.sort_order_of(DT.QUERY, self.owner_query), before)

    def test_an_item_that_no_longer_exists_is_skipped(self):
        """The client sends the whole list after a drag, so one stale name in it
        must not stop the rest of the list from being ordered."""
        before = self.sort_order_of(DT.QUERY, self.other_query)
        with self.as_user(OTHER):
            update_sort_orders(
                self.other_workbook,
                [
                    {"type": "query", "name": "does-not-exist", "sort_order": 1},
                    {"type": "query", "name": self.other_query, "sort_order": before + 5},
                ],
            )

        self.assertEqual(self.sort_order_of(DT.QUERY, self.other_query), before + 5)


class TestOrderingReachesOwnItemsOnly(OrderingReachesOwnItemsOnly, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestOrderingReachesOwnItemsOnlyWithTeamPermissions(
    OrderingReachesOwnItemsOnly, InsightsIntegrationTestCase
):
    ENABLE_PERMISSIONS = 1
