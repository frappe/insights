"""The one-time rewrite of what a number card's reading is measured against.

Three releases wrote it three ways. The patch writes every chart in the shape
the card reads, so the two older ones are read nowhere. See
`insights/patches/normalize_number_card_comparisons.py`.
"""

import frappe

from insights.patches.normalize_number_card_comparisons import execute as run_patch
from insights.patches.normalize_number_card_comparisons import normalize
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_workbook

OWNER = "Administrator"
WORKBOOK_TITLE = "Number Card Comparison Test Workbook"

PREVIOUS = {"source": "previous"}


def measure(name):
    return {
        "column_name": name.lower(),
        "data_type": "Decimal",
        "aggregation": "sum",
        "measure_name": name,
    }


def config(*readings, options=None, **rest):
    return {
        "sparkline": False,
        "number_columns": [measure(name) for name in readings],
        **({"number_column_options": options} if options is not None else {}),
        **rest,
    }


def options_of(config):
    return config["number_column_options"]


class TestNumberCardComparisons(InsightsIntegrationTestCase):
    """`normalize` on its own: the rewrite, without a document behind it."""

    SAVEPOINT = "test_number_card_comparisons"

    def test_the_chart_flag_becomes_one_previous_comparison_per_reading(self):
        chart = config("Revenue", "Profit", comparison=True)

        self.assertTrue(normalize(chart))

        self.assertNotIn("comparison", chart)
        self.assertEqual([o["comparison"] for o in options_of(chart)], [PREVIOUS, PREVIOUS])

    def test_a_reading_that_names_its_own_keeps_it(self):
        named = {"comparison": {"source": "constant", "value": 10}}
        chart = config("Revenue", "Profit", options=[named, {}], comparison=True)

        normalize(chart)

        self.assertEqual(options_of(chart)[0]["comparison"], named["comparison"])
        self.assertEqual(options_of(chart)[1]["comparison"], PREVIOUS)

    def test_a_reference_list_becomes_the_movement_and_the_target(self):
        chart = config(
            "Revenue",
            options=[
                {
                    "references": [
                        {"source": "previous", "label": "vs last month"},
                        {"source": "constant", "value": 400, "show": "attainment"},
                    ]
                }
            ],
        )

        normalize(chart)

        beside = options_of(chart)[0]
        self.assertNotIn("references", beside)
        self.assertEqual(
            beside["comparison"],
            {"source": "previous", "show": "change", "label": "vs last month"},
        )
        self.assertEqual(beside["target"], {"value": 400})

    def test_a_reading_that_named_no_reference_compares_nothing(self):
        # An author who removed the last one meant to, so the chart's own flag
        # does not come back for it.
        chart = config("Revenue", options=[{"references": []}], comparison=True)

        normalize(chart)

        self.assertEqual(options_of(chart)[0], {})

    def test_a_chart_already_in_the_shape_is_left_alone(self):
        chart = config("Revenue", options=[{"comparison": PREVIOUS}])

        self.assertFalse(normalize(chart))

    def test_a_second_run_changes_nothing(self):
        chart = config("Revenue", comparison=True)

        normalize(chart)
        once = frappe.as_json(chart)
        normalize(chart)

        self.assertEqual(frappe.as_json(chart), once)


class TestNumberCardComparisonPatch(InsightsIntegrationTestCase):
    SAVEPOINT = "test_number_card_comparison_patch"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name

    @classmethod
    def after_class(cls):
        for chart in frappe.get_all(DT.CHART, filters={"workbook": cls.workbook}, pluck="name"):
            frappe.delete_doc(DT.CHART, chart, force=True)
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True)

    def test_the_stored_chart_is_rewritten(self):
        chart = (
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "KPIs",
                    "workbook": self.workbook,
                    "chart_type": "Number",
                    "config": config("Revenue", comparison=True),
                }
            )
            .insert()
            .name
        )

        run_patch()

        stored = frappe.parse_json(frappe.db.get_value(DT.CHART, chart, "config"))
        self.assertNotIn("comparison", stored)
        self.assertEqual(options_of(stored)[0]["comparison"], PREVIOUS)
