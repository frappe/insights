import frappe

from insights.insights.doctype.insights_chart_v3.chart_query import (
    derive_operations,
    sparkline_operations,
)
from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.tests.base import InsightsIntegrationTestCase


class IbisQueryBuilderTestCase(InsightsIntegrationTestCase):
    def make_query_doc(self, operations):
        return frappe._dict(
            name=self.__class__.__name__,
            title=self.__class__.__name__,
            use_live_connection=0,
            operations=frappe.as_json(operations),
        )

    def build_query(self, operations):
        return IbisQueryBuilder(self.make_query_doc(operations)).build()


class TestIbisQueryBuilderGranularity(IbisQueryBuilderTestCase):
    def make_time_source_operations(self):
        return [
            {
                "type": "code",
                "code": """
results = [
    {"posting_time": "09:15:42.123", "label": "alpha"},
    {"posting_time": "09:15:42.987", "label": "beta"},
    {"posting_time": "14:33:19.111", "label": "gamma"},
]
""",
            },
            {
                "type": "cast",
                "column": {"type": "column", "column_name": "posting_time"},
                "data_type": "Time",
            },
        ]

    def test_summary_query_groups_time_values_by_supported_granularities(self):
        cases = [
            ("hour", {"09:00:00": 2, "14:00:00": 1}),
            ("minute", {"09:15:00": 2, "14:33:00": 1}),
            ("second", {"09:15:42": 2, "14:33:19": 1}),
        ]

        for granularity, expected in cases:
            with self.subTest(granularity=granularity):
                query = self.build_query(
                    [
                        *self.make_time_source_operations(),
                        {
                            "type": "summarize",
                            "measures": [
                                {"measure_name": "row_count", "column_name": "label", "aggregation": "count"}
                            ],
                            "dimensions": [
                                {
                                    "column_name": "posting_time",
                                    "data_type": "Time",
                                    "granularity": granularity,
                                    "dimension_name": "posting_time_bucket",
                                }
                            ],
                        },
                        {
                            "type": "order_by",
                            "column": {"type": "column", "column_name": "posting_time_bucket"},
                            "direction": "asc",
                        },
                    ]
                )

                result = query.execute()
                actual = dict(zip(result["posting_time_bucket"], result["row_count"], strict=False))

                self.assertEqual(actual, expected)

    def test_summary_query_rejects_calendar_buckets_for_time_columns(self):
        operations = [
            *self.make_time_source_operations(),
            {
                "type": "summarize",
                "measures": [{"measure_name": "row_count", "column_name": "label", "aggregation": "count"}],
                "dimensions": [
                    {
                        "column_name": "posting_time",
                        "data_type": "Time",
                        "granularity": "month",
                        "dimension_name": "posting_time_bucket",
                    }
                ],
            },
        ]

        with self.assertRaises(frappe.ValidationError) as exc:
            self.build_query(operations)

        self.assertIn("Supported granularities: second, minute, hour", str(exc.exception))


class TestIbisPivotWider(IbisQueryBuilderTestCase):
    def pivot_totals(self, sales, max_column_values):
        """Revenue by month split by region, one column total per region kept."""
        operations = [
            {"type": "code", "code": f"results = {sales}"},
            {
                "type": "pivot_wider",
                "rows": [{"column_name": "month", "data_type": "String", "dimension_name": "month"}],
                "columns": [{"column_name": "region", "data_type": "String", "dimension_name": "region"}],
                "values": [
                    {
                        "column_name": "amount",
                        "data_type": "Integer",
                        "aggregation": "sum",
                        "measure_name": "revenue",
                    }
                ],
                "max_column_values": max_column_values,
            },
        ]

        result = self.build_query(operations).execute()
        return result.drop(columns=["month"]).sum().to_dict()

    def test_pivot_keeps_the_biggest_split_value_out_of_others(self):
        # "zulu" sorts last but sells the most, so an alphabetical cut would
        # hide the biggest series inside "Others"
        sales = [
            {"month": "2026-01", "region": "alpha", "amount": 10},
            {"month": "2026-01", "region": "bravo", "amount": 5},
            {"month": "2026-01", "region": "zulu", "amount": 100},
            {"month": "2026-02", "region": "alpha", "amount": 20},
            {"month": "2026-02", "region": "zulu", "amount": 200},
        ]

        self.assertEqual(self.pivot_totals(sales, 2), {"alpha": 30, "zulu": 300, "Others": 5})

    def test_pivot_adds_no_others_column_when_it_cuts_nothing(self):
        # as many regions as the cap allows, so "Others" would hold nothing
        sales = [
            {"month": "2026-01", "region": "alpha", "amount": 10},
            {"month": "2026-02", "region": "zulu", "amount": 200},
        ]

        self.assertEqual(self.pivot_totals(sales, 2), {"alpha": 10, "zulu": 200})


class TestIbisWindowedNumberCard(IbisQueryBuilderTestCase):
    """The window a number card derives, executed.

    Derivation names the span and the engine turns it into dates, so the two
    halves of a windowed card only meet here.
    """

    def windowed_result(self, config, sales):
        return self.result_of(derive_operations("Number", "sales", config), sales)

    def result_of(self, derived, sales):
        return self.build_query(
            [
                {"type": "code", "code": f"results = {sales}"},
                {
                    "type": "cast",
                    "column": {"type": "column", "column_name": "posting_date"},
                    "data_type": "Date",
                },
                *derived[1:],
            ]
        ).execute()

    def revenue_by_window(self, config):
        sales = [
            {"posting_date": "2026-08-05", "amount": 30},
            {"posting_date": "2026-08-09", "amount": 70},
            {"posting_date": "2026-08-20", "amount": 500},  # after the anchor
            {"posting_date": "2026-07-05", "amount": 400},  # before the window
            {"posting_date": "2025-08-05", "amount": 60},
            {"posting_date": "2025-08-20", "amount": 900},  # after the shifted anchor
        ]
        return list(self.windowed_result(config, sales)["Revenue"])

    def config(self, comparison=None, span="month to date"):
        return {
            "sparkline": False,
            "number_columns": [
                {
                    "aggregation": "sum",
                    "column_name": "amount",
                    "data_type": "Decimal",
                    "measure_name": "Revenue",
                }
            ],
            "date_column": {
                "column_name": "posting_date",
                "data_type": "Date",
                "dimension_name": "posting_date",
            },
            "window": {"span": span, "anchor": "2026-08-10"},
            "number_column_options": [{"comparison": comparison} if comparison else {}],
        }

    def test_a_window_reads_the_days_it_covers(self):
        self.assertEqual(self.revenue_by_window(self.config()), [100])

    def test_a_comparison_window_is_the_row_before_the_reading(self):
        comparison = {"source": "window", "shift": {"unit": "fiscal year", "count": -1}}
        self.assertEqual(self.revenue_by_window(self.config(comparison)), [60, 100])

    def test_a_window_of_several_periods_is_one_row_holding_the_whole_window(self):
        """`last 3 months` covers three months and reads as one number.

        Grouped by the month it names, the window comes back as three rows and
        the card reads the newest month as if it were the three months. Grouping
        by the window is what makes every span one row.
        """
        sales = [
            {"posting_date": "2026-05-15", "amount": 10},
            {"posting_date": "2026-06-15", "amount": 20},
            {"posting_date": "2026-07-15", "amount": 30},
            {"posting_date": "2025-05-15", "amount": 1},
            {"posting_date": "2025-06-15", "amount": 2},
            {"posting_date": "2025-07-15", "amount": 4},
            {"posting_date": "2026-08-05", "amount": 500},  # the anchor's own month
            {"posting_date": "2026-04-30", "amount": 400},  # before the window
        ]
        comparison = {"source": "window", "shift": {"unit": "year", "count": -1}}
        result = self.windowed_result(self.config(comparison, span="last 3 months"), sales)

        self.assertEqual(list(result["Revenue"]), [7, 60])
        # the window is named by the date it starts on, and the card reads the
        # last row, so this order is the contract the number adapter reads
        self.assertEqual(
            [str(window)[:10] for window in result["posting_date"]],
            ["2025-05-01", "2026-05-01"],
        )

    def test_a_sparkline_reads_the_window_one_day_at_a_time(self):
        """The card's own rows are one per window. The picture under the number
        is the same window split by the grain below the span's unit."""
        sales = [
            {"posting_date": "2026-08-05", "amount": 30},
            {"posting_date": "2026-08-05", "amount": 5},
            {"posting_date": "2026-08-09", "amount": 70},
            {"posting_date": "2026-08-20", "amount": 500},  # after the anchor
            {"posting_date": "2026-07-05", "amount": 400},  # before the window
            {"posting_date": "2025-08-05", "amount": 60},  # the comparison window
        ]
        comparison = {"source": "window", "shift": {"unit": "year", "count": -1}}
        config = {**self.config(comparison), "sparkline": True}

        result = self.result_of(sparkline_operations("Number", "sales", config), sales)

        self.assertEqual(
            [str(day)[:10] for day in result["posting_date"]],
            ["2026-08-05", "2026-08-09"],
        )
        self.assertEqual(list(result["Revenue"]), [35, 70])
        # the number itself is unmoved by the second query
        self.assertEqual(list(self.windowed_result(config, sales)["Revenue"]), [60, 105])
