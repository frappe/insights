"""Does a chart's config derive the query the chart is meant to draw?

Every chart type has a case here, and a type with no case is a failure — this
is the only place that says what a config turns into, so a new chart type is
undrawable until it lands in `chart_derivation_fixtures`.

The cases used to be diffed against the queries the browser derived and the
shipped workbooks carried. That check did its job: the port matched, chart for
chart, so the browser's output was written into the fixtures and the caches it
came from are gone.

Read `insights/insights/doctype/insights_chart_v3/chart_query.py` for what is
being derived.
"""

import json
import unittest

from frappe import _

from insights.insights.doctype.insights_chart_v3.chart_query import (
    comparison_timespans,
    config_errors,
    derive_operations,
    sparkline_operations,
)
from insights.tests.factories import chart_derivation_fixtures, derivation_case

CHART_TYPES = {
    "Bar",
    "Line",
    "Row",
    "Number",
    "Donut",
    "Funnel",
    "Table",
    "Map",
    "Bubble",
    "Sankey",
    "Heatmap",
}


def comparable(operations):
    """The operations, minus what says nothing about the query that runs.

    A fixture names its source query by name and leaves the workbook beside it
    at zero, the placeholder a query that is not on a site yet carries. The name
    is what resolves the reference, so the placeholder is all the comparison can
    ask for.
    """
    operations = json.loads(json.dumps(operations))
    for operation in operations:
        table = operation.get("table") or {}
        if "workbook" in table:
            table["workbook"] = 0
    return operations


def _windowed_config(span="month to date", compare=None):
    """A number card reading one measure over a window, and what compares it."""
    comparison = {"source": compare} if compare else {}
    return {
        "sparkline": False,
        "number_columns": [
            {
                "aggregation": "sum",
                "column_name": "base_net_amount",
                "data_type": "Decimal",
                "measure_name": "Revenue MTD",
            }
        ],
        "date_column": {
            "column_name": "posting_date",
            "data_type": "Date",
            "dimension_name": "posting_date",
        },
        "window": {"span": span},
        "number_column_options": [{"comparison": comparison} if comparison else {}],
    }


def _two_reading_config():
    """A card of two readings, for the options list to measure against."""
    config = _windowed_config()
    config.pop("window")
    config["number_columns"].append(
        {
            "aggregation": "sum",
            "column_name": "line_cogs",
            "data_type": "Decimal",
            "measure_name": "COGS MTD",
        }
    )
    return config


def _against_measure(column, name):
    """A comparison reading its number off a measure of its own."""
    return {
        "source": "measure",
        "measure": {
            "aggregation": "sum",
            "column_name": column,
            "data_type": "Decimal",
            "measure_name": name,
        },
    }


def _sparkline_config(span="month to date", compare=None):
    """The same card, with the trend inside its window turned on."""
    return {**_windowed_config(span, compare), "sparkline": True}


class TestChartDerivation(unittest.TestCase):
    def test_every_chart_type_derives_the_operations_it_should(self):
        for case in chart_derivation_fixtures():
            with self.subTest(chart=case["title"]):
                self.assertEqual(
                    config_errors(case["chart_type"], case["query"], case["config"]),
                    [],
                    f"{case['title']} must be drawable",
                )
                derived = derive_operations(case["chart_type"], case["query"], case["config"])
                self.assertEqual(comparable(derived), comparable(case["operations"]))

    def test_every_chart_type_is_covered(self):
        """A derivation is only checked where a case exists, so count the types."""
        covered = {case["chart_type"] for case in chart_derivation_fixtures()}
        self.assertEqual(covered, CHART_TYPES)

    def test_a_config_that_names_no_columns_cannot_be_drawn(self):
        for chart_type in (
            "Bar",
            "Number",
            "Donut",
            "Funnel",
            "Table",
            "Map",
            "Bubble",
            "Sankey",
            "Heatmap",
        ):
            with self.subTest(chart_type=chart_type):
                self.assertTrue(config_errors(chart_type, "some-query", {}))

        self.assertTrue(config_errors("Bar", "", {}), "a chart with no source query")
        self.assertTrue(config_errors("Treemap", "some-query", {}), "an unknown chart type")

    def test_a_sankey_needs_a_source_a_target_and_a_value(self):
        case = derivation_case("Sankey")

        for slot in ("source_column", "target_column", "value_column"):
            with self.subTest(slot=slot):
                config = {**case["config"], slot: {}}
                self.assertTrue(config_errors("Sankey", case["query"], config))

    def test_a_heatmap_needs_two_dimensions_and_a_value(self):
        case = derivation_case("Heatmap")

        for slot in ("x_column", "y_column", "value_column"):
            with self.subTest(slot=slot):
                config = {**case["config"], slot: {}}
                self.assertTrue(config_errors("Heatmap", case["query"], config))

    def test_a_new_axis_chart_is_only_told_its_x_axis_is_missing(self):
        """Two empty slots name the same nothing, which is not a clash."""
        self.assertEqual(config_errors("Bar", "some-query", {}), [_("X-axis is required")])

    def test_an_axis_chart_cannot_split_by_the_column_it_plots(self):
        case = derivation_case("Bar")
        config = {**case["config"], "split_by": case["config"]["x_axis"]}
        self.assertIn(
            _("X-axis and Split by cannot be the same"), config_errors("Bar", case["query"], config)
        )

    def test_a_tooltip_measure_rides_the_summarize_beside_the_drawn_ones(self):
        """One value per plotted row, which is what the tooltip prints beside the
        series. Nothing here says it is not drawn — the config does that."""
        case = derivation_case("Bar")
        measure = {
            "column_name": "name",
            "data_type": "String",
            "aggregation": "count",
            "measure_name": "order_count",
        }
        config = {**case["config"], "tooltip": {"measures": [measure]}}
        operations = derive_operations("Bar", case["query"], config)
        summarize = next(op for op in operations if op["type"] == "summarize")
        self.assertIn("order_count", [m["measure_name"] for m in summarize["measures"]])

    def test_a_split_leaves_the_tooltip_measures_out(self):
        """A split fans every measure into one column per split value, which is a
        value per mark. A tooltip extra is one value per category, so a pivot has
        nowhere to put it."""
        case = derivation_case("Bar")
        config = {
            **case["config"],
            "split_by": {
                "dimension": {
                    "column_name": "territory",
                    "data_type": "String",
                    "dimension_name": "territory",
                }
            },
            "tooltip": {
                "measures": [
                    {
                        "column_name": "name",
                        "data_type": "String",
                        "aggregation": "count",
                        "measure_name": "order_count",
                    }
                ]
            },
        }
        operations = derive_operations("Bar", case["query"], config)
        pivot = next(op for op in operations if op["type"] == "pivot_wider")
        self.assertNotIn("order_count", [m["measure_name"] for m in pivot["values"]])

    def test_a_tooltip_measure_named_after_a_drawn_one_is_dropped(self):
        """Two measures under one alias is one column, and the chart would lose
        the series to the tooltip. The Bar fixture names no series, so what it
        draws is the count a chart falls back to."""
        case = derivation_case("Bar")
        drawn = {
            "column_name": "count",
            "data_type": "Integer",
            "aggregation": "count",
            "measure_name": "count_of_rows",
        }
        config = {**case["config"], "tooltip": {"measures": [drawn]}}
        operations = derive_operations("Bar", case["query"], config)
        summarize = next(op for op in operations if op["type"] == "summarize")
        names = [m["measure_name"] for m in summarize["measures"]]
        self.assertEqual(names, ["count_of_rows"])

    def test_a_heatmap_cannot_cut_the_grid_by_one_column_twice(self):
        """Both cuts on one column collapses the grid to a diagonal line."""
        case = derivation_case("Heatmap")
        config = {**case["config"], "y_column": case["config"]["x_column"]}
        self.assertTrue(config_errors("Heatmap", case["query"], config))

    def test_a_heatmap_sorts_both_of_its_cuts(self):
        """The renderer draws each axis in the order rows name its categories, so
        the grid's order is the row order and the chart has to ask for it."""
        case = derivation_case("Heatmap")
        operations = derive_operations("Heatmap", case["query"], case["config"])
        sorts = [
            (op["column"]["column_name"], op["direction"]) for op in operations if op["type"] == "order_by"
        ]
        self.assertEqual(sorts, [("posting_date", "asc"), ("territory", "asc")])

    def test_a_heatmap_lets_the_config_turn_a_cut_around(self):
        """The chart's own sort is a default, not a rule: a config sorting the
        same column the other way moves that sort rather than adding a second."""
        case = derivation_case("Heatmap")
        config = {
            **case["config"],
            "order_by": [{"column": {"type": "column", "column_name": "posting_date"}, "direction": "desc"}],
        }
        operations = derive_operations("Heatmap", case["query"], config)
        sorts = [
            (op["column"]["column_name"], op["direction"]) for op in operations if op["type"] == "order_by"
        ]
        self.assertEqual(sorts, [("posting_date", "desc"), ("territory", "asc")])

    def test_an_axis_chart_on_a_date_runs_forwards(self):
        """A line joins its points in row order and a summarize hands back none,
        so a timeline nobody sorted draws itself doubling back on itself."""
        case = derivation_case("Line")
        config = {**case["config"], "order_by": []}
        operations = derive_operations("Line", case["query"], config)
        sorts = [
            (op["column"]["column_name"], op["direction"]) for op in operations if op["type"] == "order_by"
        ]
        self.assertEqual(sorts, [("posting_date", "asc")])

    def test_an_axis_chart_on_a_category_is_left_in_the_order_it_arrived(self):
        """Ranking is the reading on a category axis, so a chart the author never
        sorted gets no sort invented for it."""
        case = derivation_case("Bar")
        operations = derive_operations("Bar", case["query"], case["config"])
        self.assertEqual([op for op in operations if op["type"] == "order_by"], [])

    def test_a_date_axis_outranks_a_sort_on_a_measure(self):
        """ibis reads the newest sort as the primary key. The measure's sort is
        added first, so it survives as the tiebreak and the timeline still runs
        forwards."""
        case = derivation_case("Line")
        config = {
            **case["config"],
            "order_by": [{"column": {"type": "column", "column_name": "Spend"}, "direction": "desc"}],
        }
        operations = derive_operations("Line", case["query"], config)
        sorts = [
            (op["column"]["column_name"], op["direction"]) for op in operations if op["type"] == "order_by"
        ]
        self.assertEqual(sorts, [("Spend", "desc"), ("posting_date", "asc")])

    def test_a_date_axis_the_author_turned_around_stays_turned_around(self):
        """Either direction is monotone, so either one draws a line that does not
        cross itself."""
        case = derivation_case("Line")
        config = {
            **case["config"],
            "order_by": [{"column": {"type": "column", "column_name": "posting_date"}, "direction": "desc"}],
        }
        operations = derive_operations("Line", case["query"], config)
        sorts = [
            (op["column"]["column_name"], op["direction"]) for op in operations if op["type"] == "order_by"
        ]
        self.assertEqual(sorts, [("posting_date", "desc")])

    def test_a_windowed_card_filters_one_window_when_nothing_compares_it(self):
        """One window is one filter and one row. The comparison is what adds a second."""
        operations = derive_operations("Number", "sales-invoice-lines", _windowed_config())
        filter_groups = [op for op in operations if op["type"] == "filter_group"]
        self.assertEqual(len(filter_groups), 1)
        self.assertEqual(
            filter_groups[0]["filters"],
            [
                {
                    "column": {"type": "column", "column_name": "posting_date"},
                    "operator": "within",
                    "value": {"span": "month to date"},
                }
            ],
        )

    def test_a_windowed_card_leaves_its_window_for_the_engine_to_resolve(self):
        """Derivation states the span, never the dates it covers.

        `get_window` reads the clock and the fiscal calendar, so a window
        resolved here would make one config derive different operations
        tomorrow.
        """
        config = _windowed_config(compare="last year")
        first = derive_operations("Number", "sales-invoice-lines", config)
        self.assertEqual(first, derive_operations("Number", "sales-invoice-lines", config))

        spans = [f["value"]["span"] for f in first[1]["filters"]]
        self.assertEqual(spans, ["month to date", "month to date"])
        self.assertEqual(
            [f["value"].get("shift") for f in first[1]["filters"]],
            [None, {"unit": "year", "count": -1}],
        )

    def test_a_comparison_is_fetched_the_way_the_card_period_says(self):
        """The comparison states the question, the span answers it.

        The period before this one is the same span moved back by its own
        length, so a card whose period changed asks for the window its
        comparison now means, with no stored shift to fall out of step.
        """
        for span, shift in [
            ("month to date", {"unit": "month", "count": -1}),
            ("last 3 months", {"unit": "month", "count": -3}),
            ("last 3 months (include current)", {"unit": "month", "count": -4}),
            ("fiscal year to date", {"unit": "fiscal year", "count": -1}),
        ]:
            with self.subTest(span=span):
                config = _windowed_config(span, compare="previous")
                operations = derive_operations("Number", "sales-invoice-lines", config)
                filter_group = next(op for op in operations if op["type"] == "filter_group")
                self.assertEqual(
                    [f["value"].get("shift") for f in filter_group["filters"]],
                    [None, shift],
                )

    def test_a_windowed_card_sorts_its_windows_oldest_first(self):
        """The card reads the last row and compares it with the one before it, so
        the sort is what makes the newest window the reading."""
        config = _windowed_config(compare="last year")
        operations = derive_operations("Number", "sales-invoice-lines", config)
        sorts = [
            (op["column"]["column_name"], op["direction"]) for op in operations if op["type"] == "order_by"
        ]
        self.assertEqual(sorts, [("posting_date", "asc")])

    def test_a_window_groups_the_card_by_the_window_itself(self):
        """A span of several periods is still one row, because the group-by is the
        window and not the unit the span names.

        A grain belongs to the card the author configured without a window. It
        says nothing about a window, so the dimension drops it rather than let a
        viewer format a window as a year.
        """
        config = _windowed_config("last 3 months", compare="last year")
        config["date_column"]["granularity"] = "year"
        operations = derive_operations("Number", "sales-invoice-lines", config)
        summarize = next(op for op in operations if op["type"] == "summarize")
        self.assertEqual(
            summarize["dimensions"],
            [
                {
                    "column_name": "posting_date",
                    "data_type": "Date",
                    "dimension_name": "posting_date",
                    "windows": [
                        {"span": "last 3 months"},
                        {"span": "last 3 months", "shift": {"unit": "year", "count": -1}},
                    ],
                }
            ],
        )

    def test_a_card_groups_by_the_windows_it_filters_to(self):
        """The filter and the group-by name the same windows, so every row the
        filter lets through belongs to one of them."""
        config = _windowed_config(compare="last year")
        operations = derive_operations("Number", "sales-invoice-lines", config)
        filter_group = next(op for op in operations if op["type"] == "filter_group")
        summarize = next(op for op in operations if op["type"] == "summarize")
        self.assertEqual(
            [f["value"] for f in filter_group["filters"]],
            summarize["dimensions"][0]["windows"],
        )

    def test_two_values_comparing_against_the_same_window_ask_for_one_window(self):
        config = _windowed_config(compare="last year")
        config["number_columns"].append(
            {
                "aggregation": "sum",
                "column_name": "line_cogs",
                "data_type": "Decimal",
                "measure_name": "COGS MTD",
            }
        )
        config["number_column_options"].append({"comparison": {"source": "last year"}})

        operations = derive_operations("Number", "sales-invoice-lines", config)
        self.assertEqual(len(operations[1]["filters"]), 2)

    def test_each_comparison_names_the_stretch_it_reads(self):
        """Two readings asking different questions fetch two stretches, and the
        source that asked is what names each — the caller matches a row to a
        question by name, never by counting back from the end."""
        config = _windowed_config(compare="previous")
        config["number_columns"].append(
            {
                "aggregation": "sum",
                "column_name": "line_cogs",
                "data_type": "Decimal",
                "measure_name": "COGS MTD",
            }
        )
        config["number_column_options"].append({"comparison": {"source": "last year"}})

        self.assertEqual(
            comparison_timespans("Number", config),
            {
                "previous": {"span": "month to date", "shift": {"unit": "month", "count": -1}},
                "last year": {"span": "month to date", "shift": {"unit": "year", "count": -1}},
            },
        )

    def test_a_grain_period_names_no_stretch_beside_itself(self):
        """It filters nothing, so every period it has is already a row."""
        config = _windowed_config(compare="previous")
        config["window"] = {"grain": "month"}
        self.assertEqual(comparison_timespans("Number", config), {})

    def test_a_name_naming_two_measures_is_reported(self):
        """Every reading, target and comparison is read back off one result by
        name, so two measures under one name would hand one card a number the
        other one asked for."""
        config = _two_reading_config()
        config["number_column_options"] = [
            {"comparison": _against_measure("base_net_amount", "Last Month")},
            {"comparison": _against_measure("line_cogs", "Last Month")},
        ]
        errors = config_errors("Number", "sales-invoice-lines", config)
        self.assertTrue(errors)
        self.assertIn("Last Month", errors[0])

        config["number_column_options"][1]["comparison"]["measure"]["measure_name"] = "COGS Last Month"
        self.assertEqual(config_errors("Number", "sales-invoice-lines", config), [])

    def test_a_comparison_cannot_rename_a_readings_fold_either(self):
        config = _two_reading_config()
        config["number_column_options"] = [
            {"comparison": _against_measure("line_cogs", "Revenue MTD")},
        ]
        self.assertTrue(config_errors("Number", "sales-invoice-lines", config))

    def test_two_readings_measured_against_one_measure_share_one_column(self):
        """One name naming one fold twice is one column, however many cards read it."""
        config = _two_reading_config()
        config["number_column_options"] = [
            {"comparison": _against_measure("base_net_amount", "Last Month")},
            {"comparison": _against_measure("base_net_amount", "Last Month")},
        ]
        self.assertEqual(config_errors("Number", "sales-invoice-lines", config), [])

        operations = derive_operations("Number", "sales-invoice-lines", config)
        summarize = next(op for op in operations if op["type"] == "summarize")
        names = [m["measure_name"] for m in summarize["measures"]]
        self.assertEqual(names, ["Revenue MTD", "COGS MTD", "Last Month"])

    def test_a_card_with_no_slice_reads_one_number_over_the_whole_result(self):
        """A period is the only thing that cuts a card by date.

        A date column with no period behind it is the sparkline's axis, so it
        groups nothing — a card grouped by a column it does not period by would
        read whichever period the data happened to end on.
        """
        config = _windowed_config()
        config.pop("window")

        operations = derive_operations("Number", "sales-invoice-lines", config)
        self.assertEqual(
            operations,
            [
                {
                    "type": "source",
                    "table": {"type": "query", "workbook": "", "query_name": "sales-invoice-lines"},
                },
                {
                    "type": "summarize",
                    "measures": config["number_columns"],
                    "dimensions": [],
                },
            ],
        )

    def test_a_grain_period_groups_by_the_grain_and_sorts_oldest_first(self):
        """A grain filters nothing: every period the data holds comes back, and
        the sort is what makes the newest one the reading."""
        config = _windowed_config()
        config["window"] = {"grain": "month"}
        config["number_column_options"] = [{"comparison": {"source": "previous"}}]

        operations = derive_operations("Number", "sales-invoice-lines", config)
        dated = {**config["date_column"], "granularity": "month"}
        self.assertEqual(
            operations,
            [
                {
                    "type": "source",
                    "table": {"type": "query", "workbook": "", "query_name": "sales-invoice-lines"},
                },
                {
                    "type": "summarize",
                    "measures": config["number_columns"],
                    "dimensions": [dated],
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "posting_date"},
                    "direction": "asc",
                },
            ],
        )

    def test_a_granularity_on_the_date_column_is_read_as_a_grain_period(self):
        """Every card authored before a period existed grouped by the date
        column's granularity. Lifting it is what keeps their number where it
        was, for the ones nobody opens in the builder."""
        config = _windowed_config()
        config.pop("window")
        config["date_column"]["granularity"] = "month"

        lifted = _windowed_config()
        lifted["window"] = {"grain": "month"}

        self.assertEqual(
            derive_operations("Number", "sales-invoice-lines", config),
            derive_operations("Number", "sales-invoice-lines", lifted),
        )

    def test_a_grain_card_asks_for_no_second_series(self):
        """Its own rows are one per period, so they already are the series."""
        config = _sparkline_config()
        config["window"] = {"grain": "month"}

        self.assertEqual(sparkline_operations("Number", "sales-invoice-lines", config), [])

    def test_a_window_a_card_cannot_group_by_is_left_ungrouped(self):
        """A window needs a date column to be a group-by, and there is nothing to
        group a card that names none."""
        config = _windowed_config()
        config.pop("date_column")
        operations = derive_operations("Number", "sales-invoice-lines", config)
        self.assertEqual([op["type"] for op in operations], ["source", "summarize"])

    def test_a_window_with_no_date_column_is_reported(self):
        """Derivation reads a window only beside a date column, so a card missing
        one falls back to reading all time under the window's own title."""
        config = _windowed_config()
        config.pop("date_column")
        self.assertTrue(config_errors("Number", "sales-invoice-lines", config))
        self.assertEqual(config_errors("Number", "sales-invoice-lines", _windowed_config()), [])

    def test_a_window_of_the_wrong_kind_is_reported_not_read(self):
        for slot, value in [
            ("window", "month to date"),
            ("number_column_options", [{"comparison": {"measure": "revenue"}}]),
        ]:
            with self.subTest(slot=slot):
                config = {**_windowed_config(), slot: value}
                self.assertTrue(config_errors("Number", "sales-invoice-lines", config))

    def test_a_config_whose_slots_hold_the_wrong_thing_is_reported_not_raised(self):
        """A slot names a column or a measure. One holding a bare string names nothing.

        Unconfigured means the config cannot derive, and a slot of the wrong kind
        is a config that cannot derive — so it comes back as an error the caller
        can show, the same as an empty slot, never as an exception out of the
        deriver.
        """
        drawable = {
            "x_axis": {"dimension": {"column_name": "status", "data_type": "String"}},
            "y_axis": {"series": []},
        }
        self.assertEqual(config_errors("Bar", "some-query", drawable), [])

        for slot, value in [
            ("x_axis", "status"),
            ("x_axis", {"dimension": "status"}),
            ("y_axis", ["count"]),
            ("y_axis", {"series": [{"measure": "count"}]}),
            ("filters", "status = 'Open'"),
            ("order_by", [{"column": "status", "direction": "asc"}]),
            ("rows", ["status"]),
        ]:
            with self.subTest(slot=slot, value=value):
                self.assertTrue(config_errors("Bar", "some-query", {**drawable, slot: value}))

        self.assertTrue(config_errors("Bar", "some-query", "status"), "a config that is not an object")


class TestSparklineDerivation(unittest.TestCase):
    """What a windowed card's sparkline runs, beside the number itself.

    One row per window draws a two-point line, so the trend inside the window is
    a second question and a second query. Nothing new derives it: inside one
    window, a finer grain is the split.
    """

    def test_a_sparkline_splits_the_cards_own_window_one_grain_finer(self):
        operations = sparkline_operations("Number", "sales-invoice-lines", _sparkline_config())
        config = _sparkline_config()

        self.assertEqual(
            operations,
            [
                {
                    "type": "source",
                    "table": {"type": "query", "workbook": "", "query_name": "sales-invoice-lines"},
                },
                {
                    "type": "filter_group",
                    "logical_operator": "And",
                    "filters": [
                        {
                            "column": {"type": "column", "column_name": "posting_date"},
                            "operator": "within",
                            "value": {"span": "month to date"},
                        }
                    ],
                },
                {
                    "type": "summarize",
                    "measures": config["number_columns"],
                    "dimensions": [{**config["date_column"], "granularity": "day"}],
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "posting_date"},
                    "direction": "asc",
                },
            ],
        )

    def test_a_sparkline_draws_the_configured_window_and_not_the_comparison(self):
        """The comparison window answers what the number is held against. The
        picture is the window the card is read over."""
        config = _sparkline_config(compare="last year")
        operations = sparkline_operations("Number", "sales-invoice-lines", config)

        filter_group = next(op for op in operations if op["type"] == "filter_group")
        self.assertEqual([f["value"] for f in filter_group["filters"]], [{"span": "month to date"}])

    def test_a_sparkline_leaves_its_window_for_the_engine_to_resolve(self):
        """The same purity the card's own derivation holds: a span here would
        derive different operations tomorrow."""
        config = _sparkline_config()
        first = sparkline_operations("Number", "sales-invoice-lines", config)
        self.assertEqual(first, sparkline_operations("Number", "sales-invoice-lines", config))

    def test_a_sparkline_runs_under_the_cards_own_filters(self):
        """Same source, same filters. A series over rows the card never counted
        is a picture of a different number."""
        config = _sparkline_config()
        config["filters"] = {
            "logical_operator": "And",
            "filters": [
                {
                    "column": {"type": "column", "column_name": "status"},
                    "operator": "=",
                    "value": "Paid",
                }
            ],
        }
        operations = sparkline_operations("Number", "sales-invoice-lines", config)

        self.assertEqual(
            [op["type"] for op in operations],
            ["source", "filter_group", "filter_group", "summarize", "order_by"],
        )
        self.assertEqual(operations[1]["filters"], config["filters"]["filters"])

    def test_a_sparkline_measures_the_readings_and_nothing_else(self):
        """A target and a comparison are read off the card's own row, and no
        sparkline is drawn behind either."""
        config = _sparkline_config()
        target = {
            "aggregation": "sum",
            "column_name": "target_amount",
            "data_type": "Decimal",
            "measure_name": "Target",
        }
        config["number_column_options"] = [{"target": {"measure": target}}]

        operations = sparkline_operations("Number", "sales-invoice-lines", config)
        summarize = next(op for op in operations if op["type"] == "summarize")
        self.assertEqual(summarize["measures"], config["number_columns"])

    def test_the_grain_is_one_step_below_the_unit_the_span_names(self):
        for span, grain in [
            ("month to date", "day"),
            ("current month", "day"),
            ("last 3 months", "day"),
            ("current week", "day"),
            ("quarter to date", "month"),
            ("year to date", "month"),
            ("fiscal year to date", "month"),
            ("last 2 fiscal years", "month"),
        ]:
            with self.subTest(span=span):
                operations = sparkline_operations("Number", "sales-invoice-lines", _sparkline_config(span))
                summarize = next(op for op in operations if op["type"] == "summarize")
                self.assertEqual(summarize["dimensions"][0]["granularity"], grain)

    def test_a_window_with_no_finer_period_draws_no_sparkline(self):
        """A day splits into clock grains, which is a different picture from a
        period of periods."""
        self.assertEqual(
            sparkline_operations("Number", "sales-invoice-lines", _sparkline_config("current day")), []
        )

    def test_nothing_runs_for_a_card_that_asks_for_no_second_query(self):
        no_window = _sparkline_config()
        no_window.pop("window")
        no_date_column = _sparkline_config()
        no_date_column.pop("date_column")

        for name, config in [
            ("the sparkline is off", _windowed_config()),
            ("the card has no window", no_window),
            ("the card has no date column", no_date_column),
        ]:
            with self.subTest(case=name):
                self.assertEqual(sparkline_operations("Number", "sales-invoice-lines", config), [])

    def test_no_chart_type_but_a_number_card_runs_a_sparkline(self):
        for chart_type in sorted(CHART_TYPES - {"Number"}):
            with self.subTest(chart_type=chart_type):
                self.assertEqual(
                    sparkline_operations(chart_type, "sales-invoice-lines", _sparkline_config()), []
                )
