import frappe
from frappe.desk.form.load import getdoc
from frappe.utils.island import get_ui_islands

from insights.desk import DESK_ISLANDS, install_custom_fields, island_for
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
)

OWNER = "Administrator"
DESK_DASHBOARD = "Desk Island Test Dashboard"
DESK_CHART = "Desk Island Test Chart"


class TestDeskIsland(InsightsIntegrationTestCase):
    SAVEPOINT = "test_desk_island"

    @classmethod
    def before_class(cls):
        install_custom_fields()

        workbook = create_test_workbook(OWNER, title="Desk Island Test Workbook")
        query = create_test_query(OWNER, workbook.name)
        cls.chart = create_test_chart(OWNER, workbook.name, query.name)
        cls.dashboard = create_test_dashboard(OWNER, workbook.name, chart=cls.chart.name)

    @classmethod
    def after_class(cls):
        for doctype in ("Dashboard", "Dashboard Chart"):
            for name in frappe.get_all(
                doctype, filters={"name": ["like", "Desk Island Test%"]}, pluck="name"
            ):
                frappe.delete_doc(doctype, name, force=True)

        frappe.delete_doc("Insights Workbook", cls.dashboard.workbook, force=True)

    def desk_dashboard(self, insights_dashboard=None):
        return frappe.get_doc(
            {
                "doctype": "Dashboard",
                "dashboard_name": DESK_DASHBOARD,
                "insights_dashboard": insights_dashboard,
            }
        ).insert()

    def desk_chart(self, insights_chart=None):
        return frappe.get_doc(
            {
                "doctype": "Dashboard Chart",
                "chart_name": DESK_CHART,
                "chart_type": "Count",
                "document_type": "ToDo",
                "based_on": "creation",
                "filters_json": "[]",
                "insights_chart": insights_chart,
            }
        ).insert()

    def onload_of(self, doctype, name):
        frappe.local.response = frappe._dict({"docs": []})
        getdoc(doctype, name)
        return frappe.response.docs[0].get("__onload") or {}

    # @feature desk.dashboard-island desk.chart-island
    def test_island_names_are_registered(self):
        islands = get_ui_islands()
        for field in DESK_ISLANDS.values():
            self.assertIn(field["island"], islands)

    # @feature desk.dashboard-island desk.chart-island
    def test_custom_fields_are_installed(self):
        for doctype, field in DESK_ISLANDS.items():
            custom_field = frappe.get_doc("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]})
            self.assertEqual(custom_field.fieldtype, "Link")
            self.assertEqual(custom_field.options, field["options"])

    # @feature desk.dashboard-island
    def test_dashboard_without_a_link_is_not_ours(self):
        self.assertIsNone(island_for(self.desk_dashboard()))

    # @feature desk.dashboard-island
    def test_dashboard_with_a_link_is_drawn_by_the_dashboard_island(self):
        doc = self.desk_dashboard(self.dashboard.name)
        self.assertEqual(
            island_for(doc),
            {"name": "insights.dashboard", "props": {"dashboard": self.dashboard.name}},
        )

    # @feature desk.chart-island
    def test_chart_with_a_link_is_drawn_by_the_chart_island(self):
        doc = self.desk_chart(self.chart.name)
        self.assertEqual(
            island_for(doc),
            {"name": "insights.chart", "props": {"chart": self.chart.name}},
        )

    # @feature desk.chart-island
    def test_chart_without_a_link_is_not_ours(self):
        self.assertIsNone(island_for(self.desk_chart()))

    # @feature desk.dashboard-island
    def test_the_claim_rides_onload_through_getdoc(self):
        name = self.desk_dashboard(self.dashboard.name).name
        self.assertEqual(
            self.onload_of("Dashboard", name)["island"],
            {"name": "insights.dashboard", "props": {"dashboard": self.dashboard.name}},
        )

    # @feature desk.chart-island
    def test_a_chart_we_draw_carries_the_claim_through_getdoc(self):
        name = self.desk_chart(self.chart.name).name
        self.assertEqual(
            self.onload_of("Dashboard Chart", name)["island"],
            {"name": "insights.chart", "props": {"chart": self.chart.name}},
        )

    # @feature desk.dashboard-island
    def test_a_dashboard_we_do_not_draw_carries_no_key(self):
        name = self.desk_dashboard().name
        # absence is the answer desk falls back on, so an empty claim would read
        # as "an island draws this" and leave the page blank
        self.assertNotIn("island", self.onload_of("Dashboard", name))
