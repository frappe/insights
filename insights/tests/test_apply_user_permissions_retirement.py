"""Retiring the site-wide switch.

See `insights/patches/retire_site_apply_user_permissions.py`, which `bench
migrate` runs against the Singles row a released site holds.
"""

import frappe

from insights.patches.retire_site_apply_user_permissions import FIELD, SETTINGS
from insights.patches.retire_site_apply_user_permissions import execute as retire
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_chart, create_test_query, create_test_workbook

OWNER = "Administrator"
PREFIX = "Retirement Test"


class TestSiteSwitchRetirement(InsightsIntegrationTestCase):
    SAVEPOINT = "test_apply_user_permissions_retirement"

    @classmethod
    def before_class(cls):
        cls.plain = cls.make_chart("Plain")
        cls.shipped = cls.make_chart("Shipped")
        frappe.db.set_value(
            DT.WORKBOOK, frappe.db.get_value(DT.CHART, cls.shipped, "workbook"), "is_standard", 1
        )

    @classmethod
    def after_class(cls):
        for name in frappe.get_all(DT.WORKBOOK, filters={"title": ("like", f"{PREFIX}%")}, pluck="name"):
            frappe.db.set_value(DT.WORKBOOK, name, "is_standard", 0)
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)

    @classmethod
    def make_chart(cls, title):
        workbook = create_test_workbook(OWNER, title=f"{PREFIX} {title}")
        query = create_test_query(OWNER, workbook.name, title=f"{PREFIX} {title} Query")
        return create_test_chart(OWNER, workbook.name, query.name, title=f"{PREFIX} {title}").name

    def switch_was(self, value):
        """The Singles row a released site holds: "0", "1", or none at all."""
        frappe.db.delete("Singles", {"doctype": SETTINGS, "field": FIELD})
        if value is None:
            return
        frappe.db.sql(
            "insert into `tabSingles` (doctype, field, value) values (%s, %s, %s)",
            (SETTINGS, FIELD, value),
        )

    # @feature permissions.chart-run-as-owner standard.runs-as-the-reader
    def test_the_retirement_writes_nothing_to_a_chart(self):
        """The switch held only the frappe gate, and the Check moves the team
        grants and Table Restrictions with it. So a chart keeps running as its
        reader, on a switch-off site and on one that never wrote the switch."""
        for was_on in ("0", "1", None):
            with self.subTest(was_on=was_on):
                self.switch_was(was_on)
                retire()
                self.assertFalse(frappe.db.get_value(DT.CHART, self.plain, "run_as_owner"))
                self.assertFalse(frappe.db.get_value(DT.CHART, self.shipped, "run_as_owner"))
                self.assertFalse(frappe.db.exists("Singles", {"doctype": SETTINGS, "field": FIELD}))
