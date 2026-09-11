"""The pure verify helpers in the workbook skill's build template.

`skills/insights-workbook-cli/examples/build_workbook.py` is a template an agent copies,
so it never runs in this app. Its three name-set helpers are what decide whether a
workbook verifies, and each case below is a defect that shipped once.
"""

import importlib.util
import unittest
from pathlib import Path

TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "insights-workbook-cli"
    / "examples"
    / "build_workbook.py"
)


def load_template():
    spec = importlib.util.spec_from_file_location("insights_workbook_skill_template", TEMPLATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestReadConfig(unittest.TestCase):
    """`read_config` splits a chart config into the names it reads, produces and sorts by."""

    @classmethod
    def setUpClass(cls):
        cls.read_config = staticmethod(load_template().read_config)

    def test_measure_names_its_column_and_its_output(self):
        source, output, _ = self.read_config(
            {"values": [{"measure_name": "Revenue", "column_name": "base_net_total"}]}
        )
        self.assertEqual(source, {"base_net_total"})
        self.assertEqual(output, {"Revenue"})

    def test_row_count_measure_names_no_column(self):
        source, output, _ = self.read_config(
            {"number_columns": [{"measure_name": "Invoices", "column_name": "count", "aggregation": "count"}]}
        )
        self.assertEqual(source, set())
        self.assertEqual(output, {"Invoices"})

    def test_expression_measure_names_no_column(self):
        source, output, _ = self.read_config(
            {
                "number_columns": [
                    {"measure_name": "Net", "expression": {"expression": "sum(debit) - sum(credit)"}}
                ]
            }
        )
        self.assertEqual(source, set())
        self.assertEqual(output, {"Net"})

    def test_dimension_without_dimension_name_comes_out_under_its_column(self):
        """translate_dimension names by `dimension_name or column_name`."""
        source, output, sorted_by = self.read_config(
            {
                "rows": [{"column_name": "customer", "data_type": "String"}],
                "order_by": [{"column": {"column_name": "customer"}}],
            }
        )
        self.assertEqual(source, {"customer"})
        self.assertEqual(output, {"customer"})
        self.assertEqual(sorted_by - output, set(), "a sort on a plain dimension is valid")

    def test_dimension_with_dimension_name_comes_out_under_that_name(self):
        source, output, _ = self.read_config(
            {"rows": [{"dimension_name": "Customer", "column_name": "customer"}]}
        )
        self.assertEqual(source, {"customer"})
        self.assertEqual(output, {"Customer"})

    def test_granularity_keeps_the_column_name(self):
        source, output, sorted_by = self.read_config(
            {
                "x_axis": {
                    "dimension": {"column_name": "posting_date", "data_type": "Date", "granularity": "month"}
                },
                "order_by": [{"column": {"column_name": "posting_date"}}],
            }
        )
        self.assertEqual(source, {"posting_date"})
        self.assertEqual(output, {"posting_date"})
        self.assertEqual(sorted_by - output, set())

    def test_misspelled_dimension_column_is_reported(self):
        """A column and a dimension name misspelled the same way must not cancel out."""
        source, _, _ = self.read_config(
            {"x_axis": {"dimension": {"dimension_name": "postng", "column_name": "postng"}}}
        )
        self.assertEqual(source, {"postng"})

    def test_sort_by_a_measure_name_is_valid(self):
        _, output, sorted_by = self.read_config(
            {
                "values": [{"measure_name": "Order Value", "column_name": "base_grand_total"}],
                "order_by": [{"column": {"column_name": "Order Value"}}],
            }
        )
        self.assertEqual(sorted_by - output, set())

    def test_misspelled_sort_is_reported(self):
        _, output, sorted_by = self.read_config(
            {
                "values": [{"measure_name": "Order Value", "column_name": "base_grand_total"}],
                "order_by": [{"column": {"column_name": "Order Vaule"}}],
            }
        )
        self.assertEqual(sorted_by - output, {"Order Vaule"})

    def test_order_by_names_are_not_source_columns(self):
        source, _, _ = self.read_config(
            {
                "values": [{"measure_name": "Revenue", "column_name": "base_net_total"}],
                "order_by": [{"column": {"column_name": "Revenue"}}],
            }
        )
        self.assertEqual(source, {"base_net_total"})

    def test_chart_filter_column_is_read_but_not_produced(self):
        source, output, _ = self.read_config(
            {
                "filters": {
                    "logical_operator": "And",
                    "filters": [{"column": {"column_name": "status"}, "operator": "=", "value": "Paid"}],
                }
            }
        )
        self.assertEqual(source, {"status"})
        self.assertEqual(output, set())


class TestSourceTables(unittest.TestCase):
    """`source_tables` finds the real tables a pipeline reads, for the data store check."""

    @classmethod
    def setUpClass(cls):
        cls.source_tables = staticmethod(load_template().source_tables)

    def test_finds_tables_in_source_join_and_union(self):
        tables = self.source_tables(
            [
                {
                    "type": "source",
                    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabSales Invoice"},
                },
                {
                    "type": "join",
                    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabCustomer"},
                },
                {"type": "union", "table": {"type": "query", "workbook": "42", "query_name": "q2"}},
            ]
        )
        self.assertEqual(tables, {("Site DB", "tabSales Invoice"), ("Site DB", "tabCustomer")})

    def test_a_query_reference_is_not_a_table(self):
        tables = self.source_tables([{"type": "source", "table": {"type": "query", "query_name": "q1"}}])
        self.assertEqual(tables, set())


class TestQueryChain(unittest.TestCase):
    """`query_chain` decides whether a dashboard filter reaches a chart."""

    @classmethod
    def setUpClass(cls):
        cls.query_chain = staticmethod(load_template().query_chain)

    def setUp(self):
        self.operations = {
            "qA": [{"type": "source", "table": {"type": "query", "query_name": "qB"}}],
            "qB": [
                {
                    "type": "source",
                    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabX"},
                },
                {"type": "join", "table": {"type": "query", "query_name": "qC"}},
            ],
            "qC": [],
            "qZ": [],
        }

    def test_follows_references_transitively(self):
        self.assertEqual(self.query_chain("qA", self.operations), {"qA", "qB", "qC"})

    def test_an_unrelated_query_is_not_in_the_chain(self):
        self.assertNotIn("qZ", self.query_chain("qA", self.operations))

    def test_a_reference_cycle_terminates(self):
        operations = {
            "q1": [{"type": "source", "table": {"type": "query", "query_name": "q2"}}],
            "q2": [{"type": "source", "table": {"type": "query", "query_name": "q1"}}],
        }
        self.assertEqual(self.query_chain("q1", operations), {"q1", "q2"})


if __name__ == "__main__":
    unittest.main()
