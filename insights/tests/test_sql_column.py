import frappe

from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.tests.base import InsightsIntegrationTestCase

SOURCE_CODE = """
results = [
    {"idx": 1, "team": "alpha", "amount": 10, "note": None},
    {"idx": 2, "team": "alpha", "amount": 20, "note": None},
    {"idx": 3, "team": "beta", "amount": 30, "note": None},
    {"idx": 4, "team": "beta", "amount": 40, "note": None},
]
"""


class TestSQLColumnOperation(InsightsIntegrationTestCase):
    def make_query_doc(self, operations):
        return frappe._dict(
            name="SQL Column Test",
            title="SQL Column Test",
            use_live_connection=0,
            operations=frappe.as_json(operations),
        )

    def build_query(self, operations):
        return IbisQueryBuilder(self.make_query_doc(operations)).build()

    def source_operations(self):
        return [{"type": "code", "code": SOURCE_CODE}]

    def execute(self, operations):
        return self.build_query([*self.source_operations(), *operations]).execute()

    def test_plain_fragment_adds_a_column(self):
        result = self.execute(
            [
                {
                    "type": "sql_column",
                    "new_name": "double_amount",
                    "fragment": "amount * 2",
                    "data_type": "Integer",
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "idx"},
                    "direction": "asc",
                },
            ]
        )

        self.assertEqual(list(result["double_amount"]), [20, 40, 60, 80])

    def test_fragment_name_may_contain_spaces(self):
        result = self.execute(
            [
                {
                    "type": "sql_column",
                    "new_name": "Count of records ",
                    "fragment": "amount + 1",
                    "data_type": "Integer",
                }
            ]
        )

        self.assertIn("Count of records ", result.columns)

    def test_window_fragment(self):
        result = self.execute(
            [
                {
                    "type": "sql_column",
                    "new_name": "previous_amount",
                    "fragment": "lag(amount, 1) over (partition by team order by idx)",
                    "data_type": "Integer",
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "idx"},
                    "direction": "asc",
                },
            ]
        )

        self.assertEqual(list(result["previous_amount"].fillna(-1).astype(int)), [-1, 10, -1, 30])

    def test_fragment_mid_pipeline_sees_derived_columns(self):
        # the case that needs `.alias()`: a filter and a mutate come first, and the
        # fragment reads the mutated column
        result = self.execute(
            [
                {
                    "type": "filter",
                    "column": {"type": "column", "column_name": "amount"},
                    "operator": ">",
                    "value": 10,
                },
                {
                    "type": "mutate",
                    "new_name": "tripled",
                    "data_type": "Integer",
                    "expression": {"type": "expression", "expression": "amount * 3"},
                },
                {
                    "type": "sql_column",
                    "new_name": "tripled_plus_one",
                    "fragment": "tripled + 1",
                    "data_type": "Integer",
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "idx"},
                    "direction": "asc",
                },
            ]
        )

        self.assertEqual(list(result["tripled_plus_one"]), [61, 91, 121])

    def test_aggregate_composes_after_a_fragment(self):
        result = self.execute(
            [
                {
                    "type": "sql_column",
                    "new_name": "double_amount",
                    "fragment": "amount * 2",
                    "data_type": "Integer",
                },
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "measure_name": "total",
                            "column_name": "double_amount",
                            "aggregation": "sum",
                        }
                    ],
                    "dimensions": [
                        {
                            "column_name": "team",
                            "data_type": "String",
                            "dimension_name": "team",
                        }
                    ],
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "team"},
                    "direction": "asc",
                },
            ]
        )

        self.assertEqual(dict(zip(result["team"], result["total"], strict=False)), {"alpha": 60, "beta": 140})

    def test_fragment_is_transpiled_from_the_source_dialect(self):
        source = frappe.get_doc("Insights Data Source v3", "Site DB")
        self.assertEqual(source.get_sqlglot_dialect(), "mysql")

        # `locate` is MySQL-only: the query runs on DuckDB, which knows `strpos`
        result = self.execute(
            [
                {
                    "type": "sql_column",
                    "new_name": "a_at",
                    "fragment": "locate('a', team)",
                    "data_type": "Integer",
                    "data_source": "Site DB",
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "idx"},
                    "direction": "asc",
                },
            ]
        )

        self.assertEqual(list(result["a_at"]), [1, 1, 4, 4])

    def test_a_statement_is_rejected(self):
        cases = [
            "1; drop table something",
            "select 1",
            "with x as (select 1) select * from x",
            "exec sp_who",
            "(select max(amount) from _insights_sql_column)",
        ]

        for fragment in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaises(frappe.ValidationError):
                    self.execute(
                        [
                            {
                                "type": "sql_column",
                                "new_name": "smuggled",
                                "fragment": fragment,
                                "data_type": "Integer",
                            }
                        ]
                    )

    def test_an_unparsable_fragment_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            self.execute(
                [
                    {
                        "type": "sql_column",
                        "new_name": "broken",
                        "fragment": "amount ) * 2",
                        "data_type": "Integer",
                    }
                ]
            )
