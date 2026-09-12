"""The one-time repair of Sankey value aggregations.

A Sankey used to draw its source query as it stood, so nothing read the
aggregation on its value column. The server derivation reads it, and the two
functions that collapse a one-row group — `count` and `count_distinct` — flatten
every ribbon to width 1. See
`insights/patches/repair_sankey_value_aggregation.py`.
"""

import frappe

from insights.patches.repair_sankey_value_aggregation import execute as repair
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_workbook

OWNER = "Administrator"
WORKBOOK_TITLE = "Sankey Repair Test Workbook"


def value_column(aggregation, measure_name):
    return {
        "column_name": "value",
        "data_type": "Integer",
        "aggregation": aggregation,
        "measure_name": measure_name,
    }


def sankey_config(aggregation, measure_name):
    return {
        "source_column": {"column_name": "source", "dimension_name": "source", "data_type": "String"},
        "target_column": {"column_name": "target", "dimension_name": "target", "data_type": "String"},
        "value_column": value_column(aggregation, measure_name),
    }


class TestSankeyAggregationRepair(InsightsIntegrationTestCase):
    SAVEPOINT = "test_sankey_aggregation_repair"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name

    @classmethod
    def after_class(cls):
        for chart in frappe.get_all(DT.CHART, filters={"workbook": cls.workbook}, pluck="name"):
            frappe.delete_doc(DT.CHART, chart, force=True)
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True)

    def create_chart(self, chart_type, config):
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": f"{chart_type} repair fixture",
                "workbook": self.workbook,
                "chart_type": chart_type,
                "config": config,
            }
        ).insert()
        return chart.name

    def config_of(self, chart):
        return frappe.parse_json(frappe.db.get_value(DT.CHART, chart, "config"))

    def test_a_counting_sankey_is_repaired(self):
        chart = self.create_chart("Sankey", sankey_config("count", "count_of_value"))

        repair()

        self.assertEqual(
            self.config_of(chart)["value_column"],
            value_column("sum", "sum_of_value"),
            "the aggregation and the measure name must move together",
        )

    def test_a_distinct_counting_sankey_is_repaired(self):
        chart = self.create_chart("Sankey", sankey_config("count_distinct", "count_distinct_of_value"))

        repair()

        self.assertEqual(self.config_of(chart)["value_column"], value_column("sum", "sum_of_value"))

    def test_a_measure_name_the_author_typed_is_kept(self):
        chart = self.create_chart("Sankey", sankey_config("count", "Sessions"))

        repair()

        self.assertEqual(
            self.config_of(chart)["value_column"],
            value_column("sum", "Sessions"),
            "a name that does not spell out the old function says nothing about it",
        )

    def test_a_summing_sankey_is_left_alone(self):
        config = sankey_config("sum", "sum_of_value")
        chart = self.create_chart("Sankey", config)

        repair()

        self.assertEqual(self.config_of(chart), config)

    def test_a_counting_chart_of_another_type_is_left_alone(self):
        config = {
            "x_axis": {"dimension": {"column_name": "source", "dimension_name": "source"}},
            "y_axis": {"series": [{"measure": value_column("count", "count_of_value")}]},
        }
        chart = self.create_chart("Bar", config)

        repair()

        self.assertEqual(self.config_of(chart), config)

    def test_a_second_run_changes_nothing(self):
        chart = self.create_chart("Sankey", sankey_config("count", "count_of_value"))

        repair()
        once = self.config_of(chart)
        repair()

        self.assertEqual(self.config_of(chart), once)
