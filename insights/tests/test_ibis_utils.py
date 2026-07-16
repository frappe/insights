from unittest.mock import patch

import frappe
import ibis

import insights
from insights.insights.doctype.insights_data_source_v3 import ibis_utils
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
    _get_single_backend,
)
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


class TestMixedBackendError(InsightsIntegrationTestCase):
    """A query that spans two backends must fail with an actionable message
    instead of ibis's bare 'Multiple backends found for this expression'."""

    def _two_backend_join(self):
        left = ibis.sqlite.connect()
        left.create_table("left_tbl", {"id": [1, 2, 3]})
        right = ibis.duckdb.connect()
        right.create_table("right_tbl", {"id": [1, 2, 3]})
        lt, rt = left.table("left_tbl"), right.table("right_tbl")
        return left, right, lt.join(rt, lt.id == rt.id)

    def test_single_backend_resolves_normally(self):
        left, _right, _expr = self._two_backend_join()
        self.assertIsNotNone(_get_single_backend(left.table("left_tbl")))

    def test_stored_and_live_mix_names_the_live_source(self):
        left, right, expr = self._two_backend_join()
        insights.db_connections["mixed_backend_live"] = left
        self.addCleanup(insights.db_connections.pop, "mixed_backend_live", None)

        # treat the right (duckdb) backend as the warehouse/stored side
        with patch.object(ibis_utils, "is_warehouse", lambda backend: backend is right):
            with self.assertRaises(frappe.ValidationError) as exc:
                _get_single_backend(expr)

        message = frappe.utils.strip_html(str(exc.exception))
        self.assertIn("stored data", message)
        self.assertIn("mixed_backend_live", message)
        self.assertIn("data store", message)

    def test_multiple_live_sources_are_listed(self):
        left, right, expr = self._two_backend_join()
        insights.db_connections["live_source_a"] = left
        insights.db_connections["live_source_b"] = right
        self.addCleanup(insights.db_connections.pop, "live_source_a", None)
        self.addCleanup(insights.db_connections.pop, "live_source_b", None)

        with self.assertRaises(frappe.ValidationError) as exc:
            _get_single_backend(expr)

        message = frappe.utils.strip_html(str(exc.exception))
        self.assertIn("different data sources", message)
        self.assertIn("live_source_a", message)
        self.assertIn("live_source_b", message)
