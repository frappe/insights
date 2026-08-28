"""A v2 chart names a column, a v3 chart names a typed dimension or measure.

The translation has to fill in what v2 never stored: the type of every result
column, the aggregation a measure carries, and - on a dashboard - which chart a
filter reaches. Where v3 has nothing to hold what v2 rendered (a progress bar
against a target, a full pie), the chart still converts and the loss is named,
because a migrator that drops a chart in silence is worse than one that says
what it could not carry.
"""

from frappe.tests import UnitTestCase

from insights.migrator.v2_charts import (
    ColumnTypes,
    chart_from_dashboard_item,
    translate_chart,
)
from insights.migrator.v2_dashboards import filter_type_of, translate_dashboard, translate_layout

COLUMNS = [
    {"name": "Creation", "type": "Datetime", "role": "dimension"},
    {"name": "Territory", "type": "String", "role": "dimension"},
    {"name": "Count of Records", "type": "Integer", "role": "measure"},
    {"name": "Revenue", "type": "Decimal", "role": "measure"},
]


def gap_kinds(translated):
    return {gap.kind for gap in translated.gaps}


def v2_chart(chart_type, options, name="chart1", query="QRY-0001"):
    return {"name": name, "chart_type": chart_type, "query": query, "options": options}


class TestChartTypesTranslate(UnitTestCase):
    def translate(self, chart_type, options, columns=COLUMNS):
        return translate_chart(v2_chart(chart_type, options), columns)

    def test_a_line_chart_keeps_its_axes_and_its_line_options(self):
        translated = self.translate(
            "Line",
            {
                "xAxis": "Creation",
                "yAxis": ["Count of Records"],
                "smoothLines": True,
                "showArea": True,
                "showPoints": True,
            },
        )
        self.assertEqual(translated.chart_type, "Line")
        self.assertEqual(translated.config["x_axis"]["dimension"]["column_name"], "Creation")
        self.assertEqual(translated.config["x_axis"]["dimension"]["data_type"], "Datetime")
        self.assertEqual(translated.config["y_axis"]["series"][0]["type"], "line")
        self.assertTrue(translated.config["y_axis"]["smooth"])
        self.assertTrue(translated.config["y_axis"]["show_area"])
        self.assertTrue(translated.config["y_axis"]["show_data_points"])

    def test_a_measure_is_summed_because_the_v2_query_already_grouped(self):
        translated = self.translate("Line", {"xAxis": "Creation", "yAxis": ["Revenue"]})
        measure = translated.config["y_axis"]["series"][0]["measure"]
        self.assertEqual(
            measure,
            {
                "measure_name": "Revenue",
                "column_name": "Revenue",
                "data_type": "Decimal",
                "aggregation": "sum",
            },
        )

    def test_a_bar_chart_keeps_its_stacking_and_its_label_rotation(self):
        translated = self.translate(
            "Bar",
            {
                "xAxis": [{"column": "Territory"}],
                "yAxis": [{"column": "Revenue", "series_options": {"type": "bar"}}],
                "stack": True,
                "rotateLabels": "90",
            },
        )
        self.assertEqual(translated.chart_type, "Bar")
        self.assertTrue(translated.config["y_axis"]["stack"])
        self.assertEqual(translated.config["x_axis"]["label_rotation"], 90)

    def test_a_row_chart_stays_a_row_chart(self):
        translated = self.translate("Row", {"xAxis": "Territory", "yAxis": ["Revenue"]})
        self.assertEqual(translated.chart_type, "Row")
        self.assertEqual(translated.config["y_axis"]["series"][0]["type"], "bar")

    def test_a_mixed_axis_chart_becomes_an_axis_chart_with_a_type_per_series(self):
        translated = self.translate(
            "Mixed Axis",
            {
                "xAxis": [{"column": "Creation"}],
                "yAxis": [
                    {"column": "Revenue", "series_options": {"type": "line"}},
                    {"column": "Count of Records", "series_options": {"type": "bar"}},
                ],
                "splitYAxis": True,
            },
        )
        self.assertEqual(translated.chart_type, "Line")
        series = translated.config["y_axis"]["series"]
        self.assertEqual([s["type"] for s in series], ["line", "bar"])
        self.assertEqual([s["align"] for s in series], ["Left", "Right"])

    def test_a_second_x_axis_column_becomes_a_split(self):
        translated = self.translate(
            "Line",
            {"xAxis": [{"column": "Creation"}, {"column": "Territory"}], "yAxis": ["Revenue"]},
        )
        self.assertEqual(translated.config["split_by"]["dimension"]["column_name"], "Territory")

    def test_a_pie_chart_becomes_a_donut_and_says_so(self):
        translated = self.translate(
            "Pie", {"xAxis": "Territory", "yAxis": "Revenue", "maxSlices": "12", "inlineLabels": True}
        )
        self.assertEqual(translated.chart_type, "Donut")
        self.assertEqual(translated.config["label_column"]["column_name"], "Territory")
        self.assertEqual(translated.config["value_column"]["column_name"], "Revenue")
        self.assertEqual(translated.config["max_slices"], 12)
        self.assertTrue(translated.config["show_inline_labels"])
        self.assertIn("pie_renders_as_donut", gap_kinds(translated))

    def test_a_funnel_keeps_its_label_and_value(self):
        translated = self.translate("Funnel", {"xAxis": "Territory", "yAxis": "Revenue"})
        self.assertEqual(translated.chart_type, "Funnel")
        self.assertEqual(translated.config["label_column"]["column_name"], "Territory")

    def test_a_number_chart_keeps_its_formatting(self):
        translated = self.translate(
            "Number", {"column": "Revenue", "shorten": True, "prefix": "Rs. ", "decimals": 2}
        )
        self.assertEqual(translated.chart_type, "Number")
        self.assertEqual(translated.config["number_columns"][0]["column_name"], "Revenue")
        self.assertTrue(translated.config["shorten_numbers"])
        self.assertEqual(translated.config["prefix"], "Rs. ")
        self.assertEqual(translated.config["decimal"], 2)
        self.assertFalse(translated.config["comparison"])

    def test_a_trend_becomes_a_number_with_a_comparison_and_a_sparkline(self):
        translated = self.translate(
            "Trend",
            {
                "valueColumn": "Revenue",
                "dateColumn": "Creation",
                "showTrendLine": True,
                "reverseDelta": True,
            },
        )
        self.assertEqual(translated.chart_type, "Number")
        self.assertTrue(translated.config["comparison"])
        self.assertTrue(translated.config["sparkline"])
        self.assertEqual(translated.config["date_column"]["column_name"], "Creation")
        self.assertTrue(translated.config["negative_is_better"])
        self.assertEqual(gap_kinds(translated), set())

    def test_a_progress_chart_keeps_its_value_and_loses_its_target(self):
        translated = self.translate(
            "Progress", {"progress": "Revenue", "target": "1000000", "targetType": "Value"}
        )
        self.assertEqual(translated.chart_type, "Number")
        self.assertEqual(translated.config["number_columns"][0]["column_name"], "Revenue")
        self.assertIn("progress_target_unsupported", gap_kinds(translated))

    def test_a_table_splits_its_columns_into_rows_and_values(self):
        translated = self.translate(
            "Table",
            {
                "columns": [{"column": "Territory"}, {"column": "Revenue"}],
                "showTotal": True,
                "filtersEnabled": True,
            },
        )
        self.assertEqual(translated.chart_type, "Table")
        self.assertEqual([r["column_name"] for r in translated.config["rows"]], ["Territory"])
        self.assertEqual([v["column_name"] for v in translated.config["values"]], ["Revenue"])
        self.assertTrue(translated.config["show_column_totals"])
        self.assertTrue(translated.config["show_filter_row"])

    def test_a_pivot_table_becomes_a_table_of_rows_columns_and_values(self):
        translated = self.translate(
            "Pivot Table",
            {
                "rows": [{"label": "Territory", "value": "Territory"}],
                "columns": [{"label": "Creation", "value": "Creation"}],
                "values": [{"label": "Revenue", "value": "Revenue"}],
            },
        )
        self.assertEqual(translated.chart_type, "Table")
        self.assertEqual([r["column_name"] for r in translated.config["rows"]], ["Territory"])
        self.assertEqual([c["column_name"] for c in translated.config["columns"]], ["Creation"])
        self.assertEqual([v["column_name"] for v in translated.config["values"]], ["Revenue"])

    def test_a_scatter_on_two_measures_becomes_a_bubble(self):
        translated = self.translate(
            "Scatter", {"xAxis": [{"column": "Revenue"}], "yAxis": [{"column": "Count of Records"}]}
        )
        self.assertEqual(translated.chart_type, "Bubble")
        self.assertEqual(translated.config["xAxis"]["column_name"], "Revenue")
        self.assertEqual(translated.config["yAxis"]["column_name"], "Count of Records")

    def test_a_scatter_on_a_dimension_falls_back_to_a_line_of_points(self):
        translated = self.translate(
            "Scatter", {"xAxis": [{"column": "Creation"}], "yAxis": [{"column": "Revenue"}]}
        )
        self.assertEqual(translated.chart_type, "Line")
        self.assertTrue(translated.config["y_axis"]["show_data_points"])
        self.assertIn("scatter_x_not_numeric", gap_kinds(translated))

    def test_an_auto_chart_becomes_a_table_of_every_column(self):
        """v2 chose the type from the result; its own last fallback is a table."""
        translated = self.translate("Auto", {})
        self.assertEqual(translated.chart_type, "Table")
        self.assertEqual(len(translated.config["rows"]) + len(translated.config["values"]), 4)
        self.assertIn("auto_type_guessed", gap_kinds(translated))

    def test_a_chart_with_no_type_converts_to_nothing_and_is_named(self):
        translated = self.translate(None, {"query": "QRY-0001"})
        self.assertIsNone(translated.chart_type)
        self.assertIn("chart_type_missing", gap_kinds(translated))
        self.assertTrue(translated.gaps[0].dropped)

    def test_a_reference_line_is_named_as_lost(self):
        translated = self.translate(
            "Line", {"xAxis": "Creation", "yAxis": ["Revenue"], "referenceLine": "Average"}
        )
        self.assertEqual(translated.chart_type, "Line")
        self.assertIn("reference_line_unsupported", gap_kinds(translated))
        self.assertFalse(any(gap.dropped for gap in translated.gaps))

    def test_an_unconfigured_axis_chart_keeps_its_type_and_names_the_hole(self):
        translated = self.translate("Row", {"xAxis": [], "yAxis": []})
        self.assertEqual(translated.chart_type, "Row")
        self.assertEqual(gap_kinds(translated), {"missing_x_axis", "missing_y_axis"})


class TestColumnTypesDrive(UnitTestCase):
    def test_without_the_query_result_the_types_are_a_guess_and_it_is_named(self):
        translated = translate_chart(
            v2_chart("Line", {"xAxis": "Creation", "yAxis": ["Revenue"]}), columns=None
        )
        self.assertEqual(translated.config["x_axis"]["dimension"]["data_type"], "String")
        self.assertIn("column_types_unknown", gap_kinds(translated))

    def test_a_column_the_query_does_not_return_is_named(self):
        translated = translate_chart(
            v2_chart("Line", {"xAxis": "Creation", "yAxis": ["Gross Margin"]}), COLUMNS
        )
        self.assertIn("column_not_in_query", gap_kinds(translated))

    def test_a_v2_label_matches_through_its_stray_whitespace_and_case(self):
        """v2 wrote "Count of records " and "Count of Records" for the same column."""
        types = ColumnTypes(COLUMNS)
        self.assertTrue(types.knows("count of records "))
        self.assertEqual(types.type_of("Count of records "), "Integer")


class TestDashboardItemsTranslate(UnitTestCase):
    def dashboard_item(self, **overrides):
        item = {
            "name": "item1",
            "item_id": "111",
            "item_type": "Line",
            "idx": 1,
            "query": None,
            "chart": None,
            "chart_title": None,
            "markdown": None,
            "filter_label": None,
            "filter_type": None,
            "filter_operator": None,
            "filter_value": None,
            "filter_links": None,
            "filter_column": None,
            "layout": '{"x": 10, "y": 30, "w": 10, "h": 10}',
            "options": "{}",
        }
        item.update(overrides)
        return item

    def translate(self, items, **kwargs):
        return translate_dashboard({"name": "DASH-01", "title": "Support"}, items, **kwargs)

    def test_a_chart_item_reads_its_query_from_the_options_when_the_column_is_empty(self):
        """Only 162 of 1103 production items fill the query column."""
        item = self.dashboard_item(options='{"query": "QRY-0035", "xAxis": "Creation", "yAxis": ["Revenue"]}')
        translated = self.translate([item])
        self.assertEqual(translated.charts[0].query, "QRY-0035")
        self.assertEqual(translated.charts[0].chart_type, "Line")

    def test_the_query_column_wins_when_both_are_filled(self):
        item = self.dashboard_item(query="QRY-0035", options='{"query": "QRY-0035"}')
        self.assertEqual(chart_from_dashboard_item(item)["query"], "QRY-0035")

    def test_a_chart_item_points_at_the_v3_chart_the_caller_named(self):
        item = self.dashboard_item(options='{"query": "QRY-0035", "xAxis": "Creation"}')
        translated = self.translate([item], chart_names={"item1": "abc123"})
        self.assertEqual(translated.items[0]["chart"], "abc123")

    def test_a_text_item_carries_its_markdown(self):
        item = self.dashboard_item(item_type="Text", markdown="<h2>Support</h2>")
        translated = self.translate([item])
        self.assertEqual(
            translated.items[0],
            {
                "type": "text",
                "text": "<h2>Support</h2>",
                "layout": {"i": "111", "x": 10, "y": 17, "w": 10, "h": 6},
            },
        )

    def test_a_layout_shrinks_because_a_v3_row_is_taller(self):
        """v2 draws 30px rows, v3 draws 52px rows, both on 20 columns."""
        self.assertEqual(
            translate_layout('{"x": 4, "y": 26, "w": 10, "h": 12}', "9"),
            {"i": "9", "x": 4, "y": 15, "w": 10, "h": 7},
        )

    def test_a_layout_never_shrinks_to_nothing(self):
        self.assertEqual(translate_layout('{"x": 0, "y": 0, "w": 5, "h": 1}', "9")["h"], 1)


CHART_ITEM = {
    "name": "item1",
    "item_id": "111",
    "item_type": "Line",
    "idx": 1,
    "query": "QRY-0035",
    "chart": "0de12fd5a0",
    "chart_title": None,
    "markdown": None,
    "layout": '{"x": 0, "y": 0, "w": 10, "h": 10}',
    "options": '{"query": "QRY-0035", "xAxis": "Creation", "yAxis": ["Revenue"]}',
}


class TestDashboardFiltersTranslate(UnitTestCase):
    def filter_item(self, **overrides):
        item = {
            "name": "item2",
            "item_id": "222",
            "item_type": "Filter",
            "idx": 2,
            "query": None,
            "chart": None,
            "chart_title": None,
            "markdown": None,
            "filter_label": "Period",
            "filter_type": "Datetime",
            "filter_operator": "between",
            "filter_value": "2022-12-01,2022-12-31",
            "filter_links": None,
            "filter_column": None,
            "layout": '{"x": 0, "y": 0, "w": 4, "h": 2}',
            "options": "{}",
        }
        item.update(overrides)
        return item

    def translate(self, items, **kwargs):
        return translate_dashboard({"name": "DASH-01", "title": "Support"}, items, **kwargs)

    def test_a_datetime_filter_becomes_a_date_filter(self):
        """v3 offers three filter types; `between` on a date still spans the whole day."""
        self.assertEqual(filter_type_of("Datetime"), "Date")
        self.assertEqual(filter_type_of("Decimal"), "Number")
        self.assertEqual(filter_type_of("Text"), "String")

    def test_a_filter_keyed_by_item_id_lands_on_the_chart_and_its_query(self):
        filter_item = self.filter_item(
            filter_links='{"111": {"column": "creation", "label": "Creation", "table": "tabIssue"}}'
        )
        translated = self.translate(
            [CHART_ITEM, filter_item],
            chart_names={"item1": "abc123"},
            query_names={"QRY-0035": "xyz789"},
        )
        item = translated.items[1]
        self.assertEqual(item["type"], "filter")
        self.assertEqual(item["filter_name"], "Period")
        self.assertEqual(item["filter_type"], "Date")
        self.assertEqual(item["links"], {"abc123": "`xyz789`.`Creation`"})

    def test_a_filter_keyed_by_chart_name_resolves_the_same_way(self):
        filter_item = self.filter_item(
            options='{"links": {"0de12fd5a0": {"column": "creation", "label": "Creation"}}}',
            filter_links=None,
        )
        translated = self.translate([CHART_ITEM, filter_item], chart_names={"item1": "abc123"})
        self.assertEqual(translated.items[1]["links"], {"abc123": "`QRY-0035`.`Creation`"})

    def test_the_link_names_the_column_the_query_returns(self):
        """v2 names the source column, v3 names the result column."""
        filter_item = self.filter_item(filter_links='{"111": {"column": "creation", "label": "Created On"}}')
        translated = self.translate(
            [CHART_ITEM, filter_item],
            columns_by_query={"QRY-0035": [{"name": "creation", "type": "Datetime"}]},
        )
        self.assertEqual(translated.items[1]["links"], {"item1": "`QRY-0035`.`creation`"})

    def test_a_link_to_a_deleted_item_is_named_not_dropped_in_silence(self):
        filter_item = self.filter_item(filter_links='{"999": {"column": "creation"}}')
        translated = self.translate([CHART_ITEM, filter_item])
        self.assertEqual(translated.items[1]["links"], {})
        self.assertIn("filter_link_dangling", {gap.kind for gap in translated.gaps})

    def test_a_between_default_becomes_the_pair_v3_reads(self):
        translated = self.translate([CHART_ITEM, self.filter_item()])
        self.assertEqual(translated.items[1]["default_operator"], "between")
        self.assertEqual(translated.items[1]["default_value"], ["2022-12-01", "2022-12-31"])

    def test_an_operator_v3_does_not_offer_drops_the_default_and_is_named(self):
        filter_item = self.filter_item(filter_operator="contains", filter_value="urgent")
        translated = self.translate([CHART_ITEM, filter_item])
        self.assertNotIn("default_operator", translated.items[1])
        self.assertIn("filter_operator_unsupported", {gap.kind for gap in translated.gaps})

    def test_two_filters_cannot_share_a_name_because_a_name_addresses_one(self):
        translated = self.translate([self.filter_item(), self.filter_item(name="item3", item_id="333")])
        self.assertEqual([item["filter_name"] for item in translated.items], ["Period", "Period 2"])
