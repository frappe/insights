"""The upgrade patches that move access onto the workbook, and the alerts that follow it.

Insights before 3.50 let an owner edit what they made and let a share on a query, chart
or dashboard grant edit. Insights 3.50 gives access through the workbook only. See
`insights/patches/share_workbooks_with_member_owners.py`.
"""

import frappe

from insights.patches.move_alert_run_as import execute as move_alert_run_as
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


def item(code, reference_name):
    """The message and data of the item `code` on `reference_name`."""
    message, data = frappe.db.get_value(
        ITEM, {"code": code, "reference_name": reference_name}, ["message", "data"]
    )
    return message, frappe.parse_json(data)


def alert_data(enabler, outcome):
    return {"alert": f"{PREFIX} Alert", "enabler": enabler, "owner": OWNER, "outcome": outcome}


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
            fields=["reference_name", "user", "message", "data"],
        )
        self.assertEqual([(i.reference_name, i.user) for i in items], [(self.workbook, None)])
        self.assertIn(AUTHOR, items[0].message)
        self.assertEqual(
            frappe.parse_json(items[0].data), {"workbook": f"{PREFIX} Workbook", "users": [AUTHOR]}
        )

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
        """A share as Insights before 3.50 wrote it, which Insights 3.50 refuses to save."""
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
        message, data = item("P7", self.workbook)
        self.assertIn(AUTHOR, message)
        self.assertEqual(
            data, {"workbook": f"{PREFIX} Workbook", "users": [AUTHOR], "shared": ["query"], "removed": []}
        )

    # @feature upgrade.member-shares-kept
    def test_a_chart_shared_with_everyone_to_edit_is_reported_not_widened(self):
        query = create_test_query(OWNER, self.workbook)
        chart = create_test_chart(OWNER, self.workbook, query.name, title=f"{PREFIX} Chart")
        self.old_share(DT.CHART, chart.name, everyone=1, write=1)

        reshape_member_shares()

        self.assertFalse(
            frappe.db.exists("DocShare", {"share_doctype": DT.WORKBOOK, "share_name": self.workbook})
        )
        message, data = item("P7", self.workbook)
        self.assertIn(f'chart "{PREFIX} Chart" with everyone to edit', message)
        self.assertEqual(
            data,
            {
                "workbook": f"{PREFIX} Workbook",
                "users": [],
                "shared": [],
                "removed": [{"kind": "chart", "title": f"{PREFIX} Chart", "write": True}],
            },
        )

    def alert_enabled_by(self, user, operations=None):
        query = create_test_query(OWNER, self.workbook, operations=operations)
        alert = frappe.get_doc(
            {
                "doctype": "Insights Alert",
                "title": f"{PREFIX} Alert",
                "channel": "Email",
                "query": query.name,
                "frequency": "Daily",
                "custom_condition": 1,
                "condition": "True",
                "message": "hello",
                "recipients": "someone@example.org",
            }
        )
        alert.db_insert()
        frappe.db.set_value("Insights Alert", alert.name, "permission_user", user, update_modified=False)
        return alert.name

    # @feature upgrade.alerts-keep-running
    def test_an_alert_its_enabler_may_not_run_runs_as_the_workbook_owner(self):
        # it reads no table, so the owner reads the rows the enabler did
        alert = self.alert_enabled_by(
            AUTHOR, operations=[{"type": "sql", "data_source": "Site DB", "raw_sql": "select 1 as one"}]
        )

        move_alert_run_as()

        self.assertEqual(frappe.db.get_value("Insights Alert", alert, "permission_user"), OWNER)
        message, data = item("P19", alert)
        self.assertIn(f"now runs as {OWNER}", message)
        self.assertEqual(data, alert_data(AUTHOR, "moved"))

    # @feature upgrade.alerts-keep-running
    def test_an_alert_is_not_moved_to_an_owner_who_may_read_other_rows(self):
        # the enabler chose the recipients, so the owner's rows must not reach them
        alert = self.alert_enabled_by(AUTHOR)

        move_alert_run_as()

        self.assertEqual(frappe.db.get_value("Insights Alert", alert, "permission_user"), AUTHOR)
        message, data = item("P19", alert)
        self.assertIn("stops at its next run", message)
        self.assertIn("reads the site table tabToDo", message)
        self.assertEqual(data, alert_data(AUTHOR, "rows_differ"))

    # @feature upgrade.alerts-keep-running
    def test_an_alert_its_enabler_may_run_is_left_alone(self):
        alert = self.alert_enabled_by(OWNER)

        move_alert_run_as()

        self.assertEqual(frappe.db.get_value("Insights Alert", alert, "permission_user"), OWNER)
        self.assertFalse(frappe.db.exists(ITEM, {"code": "P19"}))

    # @feature upgrade.alerts-keep-running
    def test_an_alert_nobody_may_run_is_reported_before_it_stops(self):
        alert = self.alert_enabled_by(AUTHOR)
        frappe.db.set_value(DT.USER, OWNER, "enabled", 0)

        move_alert_run_as()

        self.assertEqual(frappe.db.get_value("Insights Alert", alert, "permission_user"), AUTHOR)
        message, data = item("P19", alert)
        self.assertIn("stops at its next run", message)
        self.assertEqual(data, alert_data(AUTHOR, "no_editor"))
