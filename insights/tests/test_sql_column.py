import frappe
import sqlglot as sg

from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
from insights.tests.base import InsightsIntegrationTestCase

SOURCE_CODE = """
results = [
    {"idx": 1, "team": "alpha", "amount": 10, "note": "a;b"},
    {"idx": 2, "team": "alpha", "amount": 20, "note": "a;b"},
    {"idx": 3, "team": "beta", "amount": 30, "note": "a;b"},
    {"idx": 4, "team": "beta", "amount": 40, "note": "a;b"},
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

    def sql_column(self, new_name, raw_sql, **kwargs):
        return {
            "type": "sql_column",
            "new_name": new_name,
            "raw_sql": raw_sql,
            "data_type": "Integer",
            "data_source": "Site DB",
            **kwargs,
        }

    def order_by(self, column_name):
        return {
            "type": "order_by",
            "column": {"type": "column", "column_name": column_name},
            "direction": "asc",
        }

    def execute(self, operations):
        return self.build_query([*self.source_operations(), *operations]).execute()

    def test_plain_expression_adds_a_column(self):
        result = self.execute(
            [
                self.sql_column("double_amount", "amount * 2"),
                self.order_by("idx"),
            ]
        )

        self.assertEqual(list(result["double_amount"]), [20, 40, 60, 80])

    def test_name_may_contain_spaces(self):
        # unlike `mutate` and `rename`, the name is not sanitized: a migrated
        # column keeps the name the v2 charts and filters already use
        result = self.execute([self.sql_column("Count of records ", "amount + 1")])

        self.assertIn("Count of records ", result.columns)

    def test_window_expression(self):
        result = self.execute(
            [
                self.sql_column(
                    "previous_amount",
                    "lag(amount, 1) over (partition by team order by idx)",
                ),
                self.order_by("idx"),
            ]
        )

        self.assertEqual(list(result["previous_amount"].fillna(-1).astype(int)), [-1, 10, -1, 30])

    def test_a_semicolon_inside_a_string_is_allowed(self):
        result = self.execute(
            [
                self.sql_column("clean_note", "replace(note, ';', ',')", data_type="String"),
                self.order_by("idx"),
            ]
        )

        self.assertEqual(list(result["clean_note"]), ["a,b"] * 4)

    def test_expression_mid_pipeline_sees_derived_columns(self):
        # the case that needs `.alias()`: a filter and a mutate come first, and the
        # expression reads the mutated column
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
                self.sql_column("tripled_plus_one", "tripled + 1"),
                self.order_by("idx"),
            ]
        )

        self.assertEqual(list(result["tripled_plus_one"]), [61, 91, 121])

    def test_aggregate_composes_after_a_sql_column(self):
        result = self.execute(
            [
                self.sql_column("double_amount", "amount * 2"),
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
                self.order_by("team"),
            ]
        )

        self.assertEqual(dict(zip(result["team"], result["total"], strict=False)), {"alpha": 60, "beta": 140})

    def test_expression_is_transpiled_from_the_source_dialect(self):
        source = frappe.get_doc("Insights Data Source v3", "Site DB")
        dialect = source.get_sqlglot_dialect()

        # every dialect spells this differently, and only the transpile makes the
        # source's spelling run on DuckDB
        position = sg.exp.StrPosition(this=sg.column("team"), substr=sg.exp.Literal.string("a"))
        raw_sql = position.sql(dialect=dialect)

        result = self.execute([self.sql_column("a_at", raw_sql), self.order_by("idx")])

        self.assertEqual(list(result["a_at"]), [1, 1, 4, 4])

    def test_a_statement_is_rejected(self):
        cases = [
            "1; drop table something",
            "select 1",
            "with x as (select 1) select * from x",
            "exec sp_who",
            "(select max(amount) from _insights_sql_column)",
        ]

        for raw_sql in cases:
            with self.subTest(raw_sql=raw_sql):
                with self.assertRaises(frappe.ValidationError):
                    self.execute([self.sql_column("smuggled", raw_sql)])

    def test_an_unparsable_expression_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            self.execute([self.sql_column("broken", "amount ) * 2")])

    def test_a_missing_data_source_is_rejected(self):
        # without it the expression is parsed and transpiled in the wrong dialect,
        # which silently changes what the column means
        with self.assertRaises(frappe.ValidationError):
            self.execute([self.sql_column("orphan", "amount * 2", data_source="")])

    def test_an_operation_this_version_does_not_know_is_refused(self):
        """A newer client's operation must fail, not return different numbers.

        `sql_column` is the first operation to reach a release that predates it,
        so the answer to an unknown type is settled here rather than per type.
        """
        with self.assertRaises(frappe.ValidationError):
            self.execute([{"type": "operation_from_the_future", "new_name": "x"}])
