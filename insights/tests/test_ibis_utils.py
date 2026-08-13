import frappe

from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.tests.base import InsightsIntegrationTestCase


class TestIbisQueryBuilderGranularity(InsightsIntegrationTestCase):
    def make_query_doc(self, operations):
        return frappe._dict(
            name="Ibis Time Granularity Test",
            title="Ibis Time Granularity Test",
            use_live_connection=0,
            operations=frappe.as_json(operations),
        )

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

    def build_query(self, operations):
        return IbisQueryBuilder(self.make_query_doc(operations)).build()

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


class TestIbisQueryBuilderCountMeasure(InsightsIntegrationTestCase):
    """translate_measure() special-cases the synthetic "Count of records"
    pseudo-measure (query/helpers.ts `count()`) by checking column_name ==
    "count" and aggregation == "count" — both of which a real table column
    literally named "count" also satisfies when a user counts it. See #963.
    """

    def make_query_doc(self, operations):
        return frappe._dict(
            name="Ibis Count Column Test",
            title="Ibis Count Column Test",
            use_live_connection=0,
            operations=frappe.as_json(operations),
        )

    def make_source_operations(self):
        return [
            {
                "type": "code",
                "code": """
results = [
    {"count": 5, "label": "alpha"},
    {"count": None, "label": "beta"},
    {"count": 7, "label": "gamma"},
]
""",
            }
        ]

    def build_query(self, operations):
        return IbisQueryBuilder(self.make_query_doc(operations)).build()

    def test_counting_a_column_literally_named_count_counts_that_column(self):
        # COUNT is non-null-count in SQL/ibis, so the middle row (count=None)
        # is excluded: 2, not 3. Before the fix this returned 3 — every row —
        # because it silently substituted whichever column is first in the
        # table (here, "count" itself, coincidentally; on a table where a
        # different column came first it would count that one instead).
        query = self.build_query(
            [
                *self.make_source_operations(),
                {
                    "type": "summarize",
                    "measures": [
                        # measure_name here is what getAutoMeasureName() in
                        # MeasurePicker.vue produces for a real column-based
                        # measure — `${aggregation}_of_${column_name}` — never
                        # the synthetic pseudo-measure's fixed "count_of_rows".
                        {
                            "measure_name": "count_of_count",
                            "column_name": "count",
                            "aggregation": "count",
                        }
                    ],
                    "dimensions": [],
                },
            ]
        )

        result = query.execute()
        self.assertEqual(int(result["count_of_count"][0]), 2)

    def test_the_actual_synthetic_count_of_rows_measure_still_counts_every_row(self):
        # The real "Count of records" pseudo-measure from query/helpers.ts —
        # column_name/aggregation/measure_name all fixed, regardless of
        # whether the table happens to have a "count" column at all.
        #
        # Deliberately no nulls anywhere in this fixture: the synthetic
        # measure implements "count every row" as `first_column.count()`,
        # which is a non-null count of one arbitrary column, not COUNT(*) —
        # a separate, pre-existing quirk of its own (undercounts if that
        # column has nulls) that is not what #963 is about and not what
        # this test is trying to isolate.
        query = self.build_query(
            [
                {
                    "type": "code",
                    "code": """
results = [
    {"count": 5, "label": "alpha"},
    {"count": 3, "label": "beta"},
    {"count": 7, "label": "gamma"},
]
""",
                },
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "measure_name": "count_of_rows",
                            "column_name": "count",
                            "aggregation": "count",
                        }
                    ],
                    "dimensions": [],
                },
            ]
        )

        result = query.execute()
        self.assertEqual(int(result["count_of_rows"][0]), 3)
