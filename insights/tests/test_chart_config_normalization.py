"""The rewrite of every older chart config shape.

See the `normalize_chart_config` docstring in `chart_query.py` for why. The
expected outputs below are what the browser's `handleOld*` functions produced
before they were deleted.
"""

import copy

import frappe

from insights.insights.doctype.insights_chart_v3.chart_query import (
    normalize_chart_config as normalize,
)
from insights.patches.normalize_chart_configs import execute as run_patch
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_workbook

OWNER = "Administrator"
WORKBOOK_TITLE = "Chart Config Normalization Test Workbook"


def measure(name):
    return {
        "measure_name": name,
        "column_name": name.lower(),
        "data_type": "Decimal",
        "aggregation": "sum",
    }


class TestChartConfigNormalization(InsightsIntegrationTestCase):
    """`normalize_chart_config` on its own: the rewrite, without a document behind it."""

    SAVEPOINT = "test_chart_config_normalization"

    # @feature upgrade.chart-config-older-shapes
    def test_an_axis_that_was_the_dimension_itself_carries_it(self):
        dimension = {"column_name": "posting_date", "data_type": "Date", "granularity": "month"}

        written = normalize(
            {"x_axis": copy.deepcopy(dimension), "split_by": {"column_name": "region", "data_type": "String"}}
        )

        self.assertEqual(written["x_axis"], {"dimension": {**dimension, "dimension_name": "posting_date"}})
        self.assertEqual(
            written["split_by"]["dimension"],
            {"column_name": "region", "data_type": "String", "dimension_name": "region"},
        )

    # @feature upgrade.chart-config-older-shapes
    def test_a_value_axis_that_was_a_list_of_measures_draws_them_as_series(self):
        written = normalize({"y_axis": [measure("Revenue"), measure("Profit")]})

        self.assertEqual(
            written["y_axis"],
            {"series": [{"measure": measure("Revenue")}, {"measure": measure("Profit")}]},
        )

    # @feature charts.tooltip-measures upgrade.chart-config-older-shapes
    def test_a_series_hidden_from_the_chart_becomes_a_tooltip_measure(self):
        written = normalize(
            {
                "y_axis": {
                    "series": [
                        {"measure": measure("Revenue")},
                        {"measure": measure("Margin"), "hide_from_chart": True},
                    ]
                }
            }
        )

        self.assertEqual(written["y_axis"]["series"], [{"measure": measure("Revenue")}])
        self.assertEqual(written["tooltip"], {"measures": [measure("Margin")]})

    # A chart that hid every series has nothing left to plot, and the renderer
    # draws nothing at all rather than an empty plot.
    # @feature charts.tooltip-measures upgrade.chart-config-older-shapes
    def test_a_chart_that_hid_every_series_is_left_alone(self):
        config = {"y_axis": {"series": [{"measure": measure("Revenue"), "hide_from_chart": True}]}}

        self.assertEqual(normalize(config), config)

    # @feature charts.series-type upgrade.chart-config-older-shapes
    def test_a_series_marked_in_the_other_case_is_folded_to_the_one_the_renderer_reads(self):
        written = normalize(
            {
                "y_axis": {
                    "series": [
                        {"measure": measure("Revenue"), "type": "Bar"},
                        {"measure": measure("Margin"), "type": "Line"},
                    ]
                }
            }
        )

        self.assertEqual([s["type"] for s in written["y_axis"]["series"]], ["bar", "line"])

    # @feature charts.axis-min-max upgrade.chart-config-older-shapes
    def test_an_axis_bound_the_form_wrote_as_text_is_a_number_and_a_cleared_one_is_gone(self):
        written = normalize({"y_axis": {"series": [], "min": "0", "max": ""}})

        self.assertEqual(written["y_axis"]["min"], 0)
        self.assertNotIn("max", written["y_axis"])

    # @feature charts.reference-lines upgrade.chart-config-older-shapes
    def test_a_reference_line_saved_before_ids_is_given_one(self):
        written = normalize(
            {"y_axis": {"series": [{"measure": measure("Revenue")}], "reference_lines": [{"value": 500}]}}
        )

        self.assertTrue(written["y_axis"]["reference_lines"][0]["id"])

    # `statistic` read every plotted number on the axis, so it named no Measure.
    # @feature charts.reference-lines upgrade.chart-config-older-shapes
    def test_a_statistic_line_is_read_against_the_first_series_of_its_axis(self):
        written = normalize(
            {
                "y_axis": {
                    "series": [
                        {"measure": measure("Revenue")},
                        {"measure": measure("Margin"), "align": "Right"},
                    ],
                    "reference_lines": [{"statistic": "average", "align": "Right"}],
                }
            }
        )

        line = written["y_axis"]["reference_lines"][0]
        self.assertNotIn("statistic", line)
        self.assertEqual(line["aggregate"], "average")
        self.assertEqual(line["measure_name"], "Margin")
        self.assertEqual(line["axis"], "y")

    # @feature charts.config-typed-values upgrade.chart-config-older-shapes
    def test_a_number_box_that_wrote_text_holds_the_number_and_a_cleared_one_is_gone(self):
        written = normalize(
            {
                "limit": "1000",
                "max_column_values": "",
                "split_by": {
                    "dimension": {"column_name": "region", "data_type": "String"},
                    "max_split_values": "10",
                },
                "number_column_options": [{"decimal": "2"}],
            }
        )

        self.assertEqual(written["limit"], 1000)
        self.assertNotIn("max_column_values", written)
        self.assertEqual(written["split_by"]["max_split_values"], 10)
        self.assertEqual(written["number_column_options"][0]["decimal"], 2)

    # @feature charts.config-typed-values upgrade.chart-config-older-shapes
    def test_a_slot_holds_the_dimension_and_not_the_option_the_picker_handed_it(self):
        written = normalize(
            {
                "rows": [
                    {
                        "column_name": "region",
                        "data_type": "String",
                        "dimension_name": "Region",
                        "label": "region",
                        "value": "region",
                        "type": "dimension",
                        "resolvedSlots": {},
                    }
                ],
                "values": [{**measure("Revenue"), "label": "Revenue", "value": "Revenue"}],
            }
        )

        self.assertEqual(
            written["rows"][0],
            {"column_name": "region", "data_type": "String", "dimension_name": "Region"},
        )
        self.assertEqual(written["values"][0], measure("Revenue"))

    # A card's readings are measures, and the id is what a dashboard cell names
    # one by: `reading_id` in `resize_dashboard_cells.py` reads it.
    # @feature charts.number-readings upgrade.chart-config-older-shapes
    def test_a_readings_id_survives_the_slot_it_sits_in(self):
        written = normalize({"number_columns": [{**measure("Revenue"), "id": "Revenue", "label": "Revenue"}]})

        self.assertEqual(written["number_columns"][0]["id"], "Revenue")
        self.assertNotIn("label", written["number_columns"][0])

    # The rewrite drops what a picker left. It does not hold the slot to a list
    # of allowed keys, because a field a chart type gains later is nobody's
    # leftover.
    # @feature charts.config-typed-values upgrade.chart-config-older-shapes
    def test_a_slot_keeps_a_key_the_rewrite_has_no_rule_for(self):
        written = normalize(
            {"rows": [{"column_name": "region", "dimension_name": "Region", "timezone": "IST"}]}
        )

        self.assertEqual(written["rows"][0]["timezone"], "IST")

    # A Number card is the one chart type whose own older shapes are a rewrite of
    # their own, and a card that arrives from an import or a template has to be
    # stored through them too.
    # @feature charts.type-number upgrade.number-older-shapes upgrade.chart-config-older-shapes
    def test_a_number_card_is_stored_through_the_readings_own_rewrite(self):
        written = normalize(
            {"number_columns": [measure("Revenue")], "comparison": True},
            "Number",
        )

        self.assertNotIn("comparison", written)
        self.assertEqual(written["number_column_options"][0]["comparison"], {"source": "previous"})

    # A user's own text keys some of a config's maps, and a name that reads like
    # a number box is still a name.
    # @feature charts.number-format charts.config-typed-values
    def test_a_measure_named_after_a_number_box_keeps_its_format(self):
        written = normalize({"number_formats": {"max": {"decimals": "2"}, "Revenue": {"prefix": "$"}}})

        self.assertEqual(written["number_formats"]["max"], {"decimals": 2})
        self.assertEqual(written["number_formats"]["Revenue"], {"prefix": "$"})

    # @feature upgrade.chart-config-older-shapes
    def test_a_config_already_in_the_shape_is_left_alone(self):
        config = {
            "limit": 100,
            "x_axis": {
                "dimension": {"column_name": "region", "data_type": "String", "dimension_name": "region"}
            },
            "y_axis": {"series": [{"measure": measure("Revenue"), "type": "bar"}], "stack": True},
        }

        self.assertEqual(normalize(config), config)

    # @feature upgrade.chart-config-older-shapes
    def test_a_second_run_changes_nothing(self):
        config = {
            "limit": "1000",
            "x_axis": {"column_name": "region", "data_type": "String"},
            "y_axis": [measure("Revenue")],
        }

        once = normalize(config)

        self.assertEqual(normalize(once), once)


class TestChartConfigNormalizationPatch(InsightsIntegrationTestCase):
    SAVEPOINT = "test_chart_config_normalization_patch"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name

    @classmethod
    def after_class(cls):
        for chart in frappe.get_all(DT.CHART, filters={"workbook": cls.workbook}, pluck="name"):
            frappe.delete_doc(DT.CHART, chart, force=True)
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True)

    def chart(self, config):
        """A chart whose stored config is the one given, older shape and all.

        The insert normalizes, so the config is written under it — these rows
        stand for the ones stored before `validate` normalized anything.
        """
        name = (
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Trend",
                    "workbook": self.workbook,
                    "chart_type": "Line",
                    "config": {},
                }
            )
            .insert()
            .name
        )
        frappe.db.set_value(DT.CHART, name, "config", frappe.as_json(config), update_modified=False)
        return name

    # @feature upgrade.chart-config-older-shapes
    def test_a_config_saved_in_an_older_shape_is_stored_in_todays(self):
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": "Trend",
                "workbook": self.workbook,
                "chart_type": "Line",
                "config": {"x_axis": {"column_name": "region", "data_type": "String"}},
            }
        ).insert()

        stored = frappe.parse_json(frappe.db.get_value(DT.CHART, chart.name, "config"))
        self.assertEqual(
            stored["x_axis"]["dimension"],
            {"column_name": "region", "data_type": "String", "dimension_name": "region"},
        )

    # An import and a template both insert the chart, which is the one place an
    # older Number card stops being stored.
    # @feature charts.type-number upgrade.number-older-shapes
    def test_a_number_card_that_arrives_in_an_older_shape_is_stored_in_todays(self):
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": "Revenue",
                "workbook": self.workbook,
                "chart_type": "Number",
                "config": {"number_columns": [measure("Revenue")], "comparison": True},
            }
        ).insert()

        stored = frappe.parse_json(frappe.db.get_value(DT.CHART, chart.name, "config"))
        self.assertNotIn("comparison", stored)
        self.assertEqual(stored["number_column_options"][0]["comparison"], {"source": "previous"})

    # @feature upgrade.chart-config-older-shapes
    def test_the_stored_chart_is_rewritten_without_touching_when_it_was_modified(self):
        name = self.chart(
            {
                "limit": "1000",
                "x_axis": {"column_name": "region", "data_type": "String"},
                "y_axis": {"series": [{"measure": measure("Revenue"), "type": "Line"}]},
            }
        )
        modified = frappe.db.get_value(DT.CHART, name, "modified")

        run_patch()

        stored = frappe.parse_json(frappe.db.get_value(DT.CHART, name, "config"))
        self.assertEqual(stored["limit"], 1000)
        self.assertEqual(stored["x_axis"]["dimension"]["column_name"], "region")
        self.assertEqual(stored["y_axis"]["series"][0]["type"], "line")
        self.assertEqual(frappe.db.get_value(DT.CHART, name, "modified"), modified)

    # @feature upgrade.chart-config-older-shapes
    def test_a_chart_already_in_the_shape_is_not_written(self):
        name = self.chart(
            {
                "limit": 100,
                "x_axis": {
                    "dimension": {"column_name": "region", "data_type": "String", "dimension_name": "region"}
                },
                "y_axis": {"series": [{"measure": measure("Revenue")}]},
            }
        )
        before = frappe.db.get_value(DT.CHART, name, "config")

        run_patch()

        self.assertEqual(frappe.db.get_value(DT.CHART, name, "config"), before)
