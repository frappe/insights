import frappe

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
