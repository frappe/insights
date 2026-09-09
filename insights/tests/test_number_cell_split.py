"""The one-time split of the dashboard cell that drew several readings.

A cell draws one reading of a Number chart, so a cell on a chart that states
several becomes one cell per reading. The chart keeps all of them. See
`insights/patches/split_number_cells.py`.
"""

import frappe

from insights.patches.split_number_cells import execute as run_patch
from insights.patches.split_number_cells import expand_items
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_workbook

OWNER = "Administrator"
WORKBOOK_TITLE = "Number Cell Split Test Workbook"


def measure(name, column):
    return {
        "column_name": column,
        "data_type": "Decimal",
        "aggregation": "sum",
        "measure_name": name,
    }


def number_config(*readings, options=None, **rest):
    return {
        "sparkline": False,
        "number_columns": list(readings),
        "number_column_options": options or [{} for _ in readings],
        **rest,
    }


class TestNumberCellSplit(InsightsIntegrationTestCase):
    SAVEPOINT = "test_number_cell_split"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name

    @classmethod
    def after_class(cls):
        for dashboard in frappe.get_all(DT.DASHBOARD, filters={"workbook": cls.workbook}, pluck="name"):
            frappe.delete_doc(DT.DASHBOARD, dashboard, force=True)
        for chart in frappe.get_all(DT.CHART, filters={"workbook": cls.workbook}, pluck="name"):
            frappe.delete_doc(DT.CHART, chart, force=True)
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True)

    def create_chart(self, config, title="KPIs"):
        return (
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": title,
                    "workbook": self.workbook,
                    "chart_type": "Number",
                    "config": config,
                }
            )
            .insert()
            .name
        )

    def create_dashboard(self, items):
        return (
            frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Number Cell Dashboard",
                    "workbook": self.workbook,
                    "items": items,
                }
            )
            .insert()
            .name
        )

    def items_of(self, dashboard):
        return frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard, "items"))

    def cell(self, chart, **layout):
        return {
            "type": "chart",
            "chart": chart,
            "layout": {"i": "kpis", "x": 0, "y": 0, "w": 20, "h": 8, **layout},
        }

    def test_the_cell_that_held_them_becomes_one_cell_each(self):
        chart = self.create_chart(
            number_config(
                measure("Revenue", "amount"),
                measure("Profit", "profit"),
                measure("Orders", "orders"),
            )
        )
        dashboard = self.create_dashboard([self.cell(chart, x=2, w=18, y=4)])

        run_patch()

        items = self.items_of(dashboard)
        self.assertEqual([item["column"] for item in items], ["Revenue", "Profit", "Orders"])
        self.assertTrue(all(item["chart"] == chart for item in items))
        boxes = [item["layout"] for item in items]
        self.assertEqual([(b["x"], b["w"]) for b in boxes], [(2, 4), (6, 4), (10, 4)])
        self.assertEqual({b["y"] for b in boxes}, {4})
        self.assertEqual([b["i"] for b in boxes], ["kpis", "kpis-2", "kpis-3"])

    def test_the_chart_keeps_every_reading_it_states(self):
        chart = self.create_chart(number_config(measure("Revenue", "amount"), measure("Profit", "profit")))
        self.create_dashboard([self.cell(chart)])

        run_patch()

        config = frappe.parse_json(frappe.db.get_value(DT.CHART, chart, "config"))
        self.assertEqual([m["measure_name"] for m in config["number_columns"]], ["Revenue", "Profit"])

    def test_each_cell_takes_the_height_its_own_card_needs(self):
        chart = self.create_chart(
            number_config(
                measure("Revenue", "amount"),
                measure("Churn", "churn"),
                options=[{}, {"comparison": {"source": "previous"}}],
            )
        )
        dashboard = self.create_dashboard([self.cell(chart)])

        run_patch()

        self.assertEqual([item["layout"]["h"] for item in self.items_of(dashboard)], [4, 5])

    def test_the_cells_under_it_drop_past_the_new_ones(self):
        # A quarter-width cell stacks its readings, so what stood under the one
        # cell now stands where the second reading is.
        chart = self.create_chart(
            number_config(
                measure("Revenue", "amount"),
                measure("Profit", "profit"),
                measure("Orders", "orders"),
            )
        )
        below = self.cell(chart, i="note", y=8, w=20, h=4)
        below["column"] = "Revenue"
        dashboard = self.create_dashboard([self.cell(chart, w=4, h=8), below])

        run_patch()

        items = self.items_of(dashboard)
        note = next(item for item in items if item["layout"]["i"] == "note")
        stacked = [item["layout"] for item in items if item["layout"]["i"] != "note"]
        self.assertGreaterEqual(note["layout"]["y"], max(box["y"] + box["h"] for box in stacked))

    def test_a_chart_stating_one_reading_leaves_its_cell_alone(self):
        chart = self.create_chart(number_config(measure("Revenue", "amount")))
        dashboard = self.create_dashboard([self.cell(chart)])

        run_patch()

        items = self.items_of(dashboard)
        self.assertEqual(len(items), 1)
        self.assertNotIn("column", items[0])

    def test_the_charts_the_dashboard_links_stay_right(self):
        # The derived table is the charts the grid names, and the patch writes
        # more cells on the same chart — so it is still the answer afterwards.
        chart = self.create_chart(number_config(measure("Revenue", "amount"), measure("Profit", "profit")))
        dashboard = self.create_dashboard([self.cell(chart)])

        run_patch()

        doc = frappe.get_doc(DT.DASHBOARD, dashboard)
        self.assertEqual([row.chart for row in doc.linked_charts], [chart])

    def test_a_second_run_changes_nothing(self):
        chart = self.create_chart(number_config(measure("Revenue", "amount"), measure("Profit", "profit")))
        dashboard = self.create_dashboard([self.cell(chart)])

        run_patch()
        items = self.items_of(dashboard)

        run_patch()

        self.assertEqual(self.items_of(dashboard), items)


class TestNumberCellExpansion(InsightsIntegrationTestCase):
    """`expand_items` on its own: the arithmetic, without a document behind it."""

    SAVEPOINT = "test_number_cell_expansion"

    def configs(self, readings=3):
        """One Number chart named `c`, stating `readings` readings."""
        columns = [{"measure_name": name} for name in "abc"[:readings]]
        return {"c": {"sparkline": False, "number_columns": columns}}

    def test_each_cell_takes_the_width_a_dropped_cell_takes(self):
        items = [{"type": "chart", "chart": "c", "layout": {"i": "a", "x": 0, "y": 0, "w": 20, "h": 8}}]

        expand_items(items, self.configs())

        self.assertEqual([item["layout"]["w"] for item in items], [4, 4, 4])
        self.assertEqual([item["layout"]["x"] for item in items], [0, 4, 8])

    def test_a_row_that_overflows_the_cell_wraps_under_it(self):
        items = [{"type": "chart", "chart": "c", "layout": {"i": "a", "x": 2, "y": 1, "w": 8, "h": 8}}]

        expand_items(items, self.configs())

        boxes = [item["layout"] for item in items]
        self.assertEqual([(b["x"], b["y"]) for b in boxes], [(2, 1), (6, 1), (2, 5)])

    def test_every_breakpoint_the_cell_was_arranged_for_is_split_too(self):
        items = [
            {
                "type": "chart",
                "chart": "c",
                "layout": {"i": "a", "x": 0, "y": 0, "w": 20, "h": 8},
                "layouts": {"sm": {"x": 0, "y": 0, "w": 20, "h": 8}},
            }
        ]

        expand_items(items, self.configs(2))

        self.assertEqual([item["layouts"]["sm"]["w"] for item in items], [4, 4])
        self.assertEqual([item["layouts"]["sm"]["x"] for item in items], [0, 4])

    def test_a_cell_narrower_than_a_dropped_cell_stacks_the_readings(self):
        items = [{"type": "chart", "chart": "c", "layout": {"i": "a", "x": 0, "y": 0, "w": 2, "h": 8}}]

        expand_items(items, self.configs())

        self.assertEqual([item["layout"]["w"] for item in items], [2, 2, 2])
        self.assertEqual([item["layout"]["y"] for item in items], [0, 4, 8])

    def test_a_cell_that_already_names_a_reading_is_left_alone(self):
        items = [
            {
                "type": "chart",
                "chart": "c",
                "column": "b",
                "layout": {"i": "a", "x": 0, "y": 0, "w": 4, "h": 4},
            }
        ]

        self.assertFalse(expand_items(items, self.configs()))
        self.assertEqual(len(items), 1)

    def test_a_grid_holding_no_such_chart_is_left_alone(self):
        items = [{"type": "text", "text": "hello", "layout": {"i": "t", "x": 0, "y": 0, "w": 4, "h": 2}}]

        self.assertFalse(expand_items(items, self.configs()))
        self.assertEqual(len(items), 1)
