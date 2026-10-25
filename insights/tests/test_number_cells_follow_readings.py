"""A dashboard shows one cell per reading of a Number chart, and keeps doing so
as the chart's readings change. A reading added to the chart gets a cell beside
the chart's others, and a reading removed takes its cell with it. A cell the
author removed from a dashboard stays removed."""

import frappe

from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_workbook

OWNER = "Administrator"
WORKBOOK_TITLE = "Number Cells Follow Readings Test Workbook"


def reading(id):
    return {
        "id": id,
        "column_name": "amount",
        "data_type": "Decimal",
        "aggregation": "sum",
        "measure_name": id,
    }


def number_config(*ids):
    return {
        "sparkline": False,
        "number_columns": [reading(id) for id in ids],
        "number_column_options": [{} for _ in ids],
    }


def cell(chart, reading, x, y=0):
    return {
        "type": "chart",
        "chart": chart,
        "reading": reading,
        "layout": {"i": f"{reading}-cell", "x": x, "y": y, "w": 4, "h": 4},
    }


class TestNumberCellsFollowReadings(InsightsIntegrationTestCase):
    SAVEPOINT = "test_number_cells_follow_readings"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True)

    def before_test(self):
        self.chart = (
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "KPIs",
                    "workbook": self.workbook,
                    "chart_type": "Number",
                    "config": number_config("revenue"),
                }
            )
            .insert()
            .name
        )
        self.dashboard = (
            frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Readings Dashboard",
                    "workbook": self.workbook,
                    "items": [cell(self.chart, "revenue", 0)],
                }
            )
            .insert()
            .name
        )

    def set_readings(self, *ids):
        chart = frappe.get_doc(DT.CHART, self.chart)
        chart.config = number_config(*ids)
        chart.save()

    def cells(self):
        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, self.dashboard, "items"))
        return [(item.get("reading"), item["layout"]["x"], item["layout"]["y"]) for item in items]

    # @feature dashboard.number-cell-per-reading
    def test_a_reading_added_to_a_chart_gets_a_cell_beside_its_others(self):
        self.set_readings("revenue", "orders")

        self.assertEqual(self.cells(), [("revenue", 0, 0), ("orders", 4, 0)])

    # @feature dashboard.number-cell-per-reading
    def test_a_reading_removed_from_a_chart_takes_its_cell(self):
        self.set_readings("revenue", "orders")
        self.set_readings("orders")

        self.assertEqual(self.cells(), [("orders", 4, 0)])

    # @feature dashboard.number-cell-per-reading
    def test_a_cell_the_author_removed_stays_removed(self):
        self.set_readings("revenue", "orders")
        dashboard = frappe.get_doc(DT.DASHBOARD, self.dashboard)
        dashboard.items = [cell(self.chart, "revenue", 0)]
        dashboard.save()

        self.set_readings("revenue", "orders", "margin")

        self.assertEqual(self.cells(), [("revenue", 0, 0), ("margin", 4, 0)])

    # @feature dashboard.number-cell-per-reading
    def test_a_cell_naming_no_reading_leaves_with_the_first_reading_it_showed(self):
        """Such a cell, saved before cells named a reading, shows the first one.
        It would otherwise move onto the next reading, which has a cell already."""
        self.set_readings("revenue", "orders")
        dashboard = frappe.get_doc(DT.DASHBOARD, self.dashboard)
        items = frappe.parse_json(dashboard.items)
        del items[0]["reading"]
        dashboard.items = items
        dashboard.save()

        self.set_readings("orders")

        self.assertEqual(self.cells(), [("orders", 4, 0)])

    # @feature dashboard.number-cell-per-reading
    def test_a_chart_turned_into_a_number_chart_gets_a_cell_for_each_reading_its_cell_does_not_show(self):
        frappe.db.set_value(DT.CHART, self.chart, "chart_type", "Bar")
        dashboard = frappe.get_doc(DT.DASHBOARD, self.dashboard)
        items = frappe.parse_json(dashboard.items)
        del items[0]["reading"]
        dashboard.items = items
        dashboard.save()

        chart = frappe.get_doc(DT.CHART, self.chart)
        chart.chart_type = "Number"
        chart.config = number_config("revenue", "orders")
        chart.save()

        self.assertEqual(self.cells(), [(None, 0, 0), ("orders", 4, 0)])
