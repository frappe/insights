"""The date range defaults Insights 3 stored as text and never applied.

See `insights/patches/drop_unapplied_date_range_defaults.py`.
"""

import frappe

from insights.patches.drop_unapplied_date_range_defaults import execute as drop_defaults
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_dashboard, create_test_workbook
from insights.upgrade import ITEM

OWNER = "Administrator"
PREFIX = "Unapplied Range Test"


def date_filter(name, operator, value):
    return {
        "id": name,
        "type": "filter",
        "filter_name": name,
        "filter_type": "Date",
        "links": {},
        "default_operator": operator,
        "default_value": value,
    }


class TestUnappliedDateRangeDefaults(InsightsIntegrationTestCase):
    SAVEPOINT = "test_unapplied_date_range_defaults"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=PREFIX).name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)

    def filters_after_the_patch(self, *filters):
        dashboard = create_test_dashboard(OWNER, self.workbook, title=f"{PREFIX} Dashboard").name
        frappe.db.set_value(DT.DASHBOARD, dashboard, "items", frappe.as_json(list(filters)))

        drop_defaults()

        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard, "items"))
        return {item["filter_name"]: item for item in items}, dashboard

    # @feature upgrade.dashboard-filters-apply-as-before
    def test_a_range_stored_as_text_is_removed_and_reported(self):
        frappe.db.delete(ITEM)

        filters, dashboard = self.filters_after_the_patch(
            date_filter("Posted", "between", "2024-01-01,2024-01-31")
        )

        self.assertNotIn("default_value", filters["Posted"])
        self.assertEqual(filters["Posted"]["default_operator"], "between")
        message = frappe.db.get_value(ITEM, {"code": "K1", "reference_name": dashboard}, "message")
        self.assertIn("2024-01-01 to 2024-01-31", message)

    # @feature upgrade.dashboard-filters-apply-as-before
    def test_a_default_insights_3_applied_is_kept(self):
        filters, _ = self.filters_after_the_patch(
            date_filter("Posted", "between", ["2024-01-01", "2024-01-31"]),
            date_filter("Recent", "within", "Last 12 months"),
        )

        self.assertEqual(filters["Posted"]["default_value"], ["2024-01-01", "2024-01-31"])
        self.assertEqual(filters["Recent"]["default_value"], "Last 12 months")
