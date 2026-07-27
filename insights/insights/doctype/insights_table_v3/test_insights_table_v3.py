# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import ibis
from frappe.tests.utils import FrappeTestCase

from insights.insights.doctype.insights_table_v3 import insights_table_v3 as table_module
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    apply_column_permissions,
    get_permitted_columns_for_table,
)


class TestInsightsTablev3(FrappeTestCase):
    pass


class TestUserPermissionColumns(FrappeTestCase):
    """Covers the column-level (permlevel) permission filtering in apply_user_permissions."""

    def test_optional_meta_fields_are_permitted(self):
        # Regression: optional meta columns like `_assign` aren't in `valid_columns`, so
        # `get_permitted_fields` drops them. They must be added back, otherwise filtering a
        # table by user permissions silently loses the `_assign` column.
        allowed = get_permitted_columns_for_table("tabUser")

        self.assertIn("name", allowed)
        self.assertIn("_assign", allowed)
        # a regular (permlevel 0) field the admin can read
        self.assertIn("email", allowed)

    def test_no_columns_when_doctype_is_not_readable(self):
        # Guest cannot read `Role`, so no columns are permitted. The caller's row filter
        # then blocks all rows.
        frappe.set_user("Guest")
        try:
            self.assertFalse(frappe.has_permission("Role", "read"))
            self.assertEqual(get_permitted_columns_for_table("tabRole"), set())
        finally:
            frappe.set_user("Administrator")

    def test_child_table_unions_permitted_parent_columns(self):
        # `Has Role` is the child table behind User.roles. As admin (who can read User),
        # its parent's permitted columns should be returned.
        allowed = get_permitted_columns_for_table("tabHas Role")

        self.assertIn("role", allowed)
        self.assertIn("parent", allowed)
        self.assertIn("_assign", allowed)

    def test_apply_column_permissions_keeps_only_allowed(self):
        t = ibis.memtable({"name": ["a"], "secret": ["x"], "_assign": ["[]"]})

        original = table_module.get_permitted_columns_for_table
        table_module.get_permitted_columns_for_table = lambda _name: {"name", "_assign"}
        try:
            result = apply_column_permissions(t, "tabSomething")
        finally:
            table_module.get_permitted_columns_for_table = original

        # `secret` is dropped; original column order is preserved.
        self.assertEqual(list(result.columns), ["name", "_assign"])

    def test_apply_column_permissions_no_op_when_nothing_permitted(self):
        # With an empty allowed set we must NOT emit `select([])` (invalid in ibis); the
        # table is returned untouched and the row filter blocks the rows instead.
        t = ibis.memtable({"name": ["a"], "secret": ["x"]})

        original = table_module.get_permitted_columns_for_table
        table_module.get_permitted_columns_for_table = lambda _name: set()
        try:
            result = apply_column_permissions(t, "tabSomething")
        finally:
            table_module.get_permitted_columns_for_table = original

        self.assertEqual(list(result.columns), ["name", "secret"])
