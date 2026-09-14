"""Compact layout is the dashboard's own field, and it was on before it was.

The setting used to live in the browser and was on unless a reader turned it
off. The field that replaced it has been on the doctype since the v2 era with
nothing ever writing it, so every stored row holds 0 — and reading the field
alone would open the gaps in every dashboard already drawn. See
`insights/patches/close_dashboard_layout_gaps.py`.
"""

import frappe

from insights.patches.close_dashboard_layout_gaps import execute as run_patch
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_workbook

OWNER = "Administrator"
WORKBOOK_TITLE = "Compact Layout Test Workbook"


class TestDashboardCompactLayout(InsightsIntegrationTestCase):
    SAVEPOINT = "test_dashboard_compact_layout"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name
        # the field's new default reaches a running site with the patch, so a
        # site that has not migrated since reads the old one
        run_patch()

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True)

    def create_dashboard(self, title):
        return frappe.get_doc(
            {"doctype": DT.DASHBOARD, "title": title, "workbook": self.workbook, "items": []}
        ).insert()

    # @feature dashboard.compact-layout
    def test_a_new_dashboard_closes_its_gaps(self):
        self.assertEqual(self.create_dashboard("New Compact Dashboard").vertical_compact_layout, 1)

    # @feature dashboard.compact-layout
    def test_the_patch_closes_the_gaps_of_a_dashboard_drawn_before_the_field(self):
        """Nothing wrote the field, so a row from before it reads as 0 and would
        re-arrange itself on deploy."""
        dashboard = self.create_dashboard("Old Compact Dashboard").name
        frappe.db.set_value(DT.DASHBOARD, dashboard, "vertical_compact_layout", 0)
        modified = frappe.db.get_value(DT.DASHBOARD, dashboard, "modified")

        run_patch()

        self.assertEqual(frappe.db.get_value(DT.DASHBOARD, dashboard, "vertical_compact_layout"), 1)
        self.assertEqual(frappe.db.get_value(DT.DASHBOARD, dashboard, "modified"), modified)
