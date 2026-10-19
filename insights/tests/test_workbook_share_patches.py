"""The upgrade patches that move access onto the workbook.

Insights 3 let an owner edit what they made and let a share on a query, chart
or dashboard grant edit. Insights 4 gives access through the workbook only. See
`insights/patches/share_workbooks_with_member_owners.py`.
"""

import frappe

from insights.patches.reshape_member_shares import execute as reshape_member_shares
from insights.patches.share_workbooks_with_member_owners import execute as share_with_owners
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
)
from insights.upgrade import ITEM

AUTHOR = "workbook_share_patch_author@test.com"
OWNER = "workbook_share_patch_owner@test.com"
DISABLED = "workbook_share_patch_disabled@test.com"
PREFIX = "Workbook Share Patch Test"


class TestWorkbookSharePatches(InsightsIntegrationTestCase):
    SAVEPOINT = "test_workbook_share_patches"

    @classmethod
    def before_class(cls):
        create_user(AUTHOR, roles="Insights User")
        create_user(OWNER, roles="Insights User")
        create_user(DISABLED, roles="Insights User")
        frappe.db.set_value(DT.USER, DISABLED, "enabled", 0)

    @classmethod
    def after_class(cls):
        for name in frappe.get_all(DT.WORKBOOK, filters={"title": ("like", f"{PREFIX}%")}, pluck="name"):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(AUTHOR, OWNER, DISABLED)

    def before_test(self):
        frappe.db.delete(ITEM)
        self.workbook = create_test_workbook(OWNER, title=f"{PREFIX} Workbook").name

    def made_by(self, user, doctype, name):
        frappe.db.set_value(doctype, name, "owner", user, update_modified=False)

    def can(self, user, ptype):
        return bool(frappe.has_permission(DT.WORKBOOK, ptype, doc=self.workbook, user=user))

    # @feature upgrade.owners-keep-access
    def test_an_author_the_workbook_does_not_name_can_edit_it_again(self):
        query = create_test_query(OWNER, self.workbook)
        chart = create_test_chart(OWNER, self.workbook, query.name)
        self.made_by(AUTHOR, DT.CHART, chart.name)
        self.assertFalse(self.can(AUTHOR, "read"))

        share_with_owners()

        self.assertTrue(self.can(AUTHOR, "write"))
        items = frappe.get_all(
            ITEM,
            filters={"code": "P3", "reference_name": self.workbook},
            fields=["reference_name", "user", "message"],
        )
        self.assertEqual([(i.reference_name, i.user) for i in items], [(self.workbook, None)])
        self.assertIn(AUTHOR, items[0].message)

    # @feature upgrade.owners-keep-access
    def test_a_read_share_is_raised_to_edit_once(self):
        query = create_test_query(OWNER, self.workbook)
        self.made_by(AUTHOR, DT.QUERY, query.name)
        frappe.share.add_docshare(DT.WORKBOOK, self.workbook, user=AUTHOR, read=1, notify=0)

        share_with_owners()
        share_with_owners()

        self.assertEqual(
            frappe.get_all(
                "DocShare",
                filters={"share_doctype": DT.WORKBOOK, "share_name": self.workbook, "user": AUTHOR},
                fields=["read", "write"],
            ),
            [{"read": 1, "write": 1}],
        )
        self.assertEqual(frappe.db.count(ITEM, {"code": "P3", "reference_name": self.workbook}), 1)

    # @feature upgrade.owners-keep-access
    def test_an_owner_who_can_edit_or_cannot_sign_in_is_left_alone(self):
        query = create_test_query(OWNER, self.workbook)
        self.made_by(DISABLED, DT.QUERY, query.name)

        share_with_owners()

        self.assertFalse(
            frappe.db.exists("DocShare", {"share_doctype": DT.WORKBOOK, "share_name": self.workbook})
        )
        self.assertFalse(frappe.db.exists(ITEM, {"code": "P3", "reference_name": self.workbook}))

    def old_share(self, doctype, name, **flags):
        """A share as Insights 3 wrote it, which Insights 4 refuses to save."""
        frappe.get_doc(
            {"doctype": "DocShare", "share_doctype": doctype, "share_name": name, "read": 1, **flags}
        ).db_insert()

    # @feature upgrade.member-shares-kept
    def test_a_user_a_query_was_shared_with_reads_its_workbook(self):
        query = create_test_query(OWNER, self.workbook)
        self.old_share(DT.QUERY, query.name, user=AUTHOR)

        reshape_member_shares()

        self.assertTrue(self.can(AUTHOR, "read"))
        self.assertFalse(self.can(AUTHOR, "write"))
        self.assertFalse(frappe.db.exists("DocShare", {"share_doctype": DT.QUERY, "share_name": query.name}))
        message = frappe.db.get_value(ITEM, {"code": "P7", "reference_name": self.workbook}, "message")
        self.assertIn(AUTHOR, message)

    # @feature upgrade.member-shares-kept
    def test_a_chart_shared_with_everyone_to_edit_is_reported_not_widened(self):
        query = create_test_query(OWNER, self.workbook)
        chart = create_test_chart(OWNER, self.workbook, query.name, title=f"{PREFIX} Chart")
        self.old_share(DT.CHART, chart.name, everyone=1, write=1)

        reshape_member_shares()

        self.assertFalse(
            frappe.db.exists("DocShare", {"share_doctype": DT.WORKBOOK, "share_name": self.workbook})
        )
        message = frappe.db.get_value(ITEM, {"code": "P7", "reference_name": self.workbook}, "message")
        self.assertIn(f'The chart "{PREFIX} Chart"', message)
        self.assertIn("shared with everyone to edit", message)
