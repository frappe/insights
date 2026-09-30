"""The pure verify helpers in the workbook skill's build template.

`skills/insights-workbook-cli/examples/build_workbook.py` is a template an agent copies,
so it never runs in this app. Its name-set helpers are what decide whether a
workbook verifies, and each case below is a defect that shipped once.
"""

import importlib.util
import io
import unittest
from contextlib import redirect_stdout
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
    """`read_config` finds the names a chart config reads from its base query."""

    @classmethod
    def setUpClass(cls):
        cls.read_config = staticmethod(load_template().read_config)

    # @feature tooling.workbook-skill-verify
    def test_measure_names_its_column(self):
        source = self.read_config({"values": [{"measure_name": "Revenue", "column_name": "base_net_total"}]})
        self.assertEqual(source, {"base_net_total"})

    # @feature tooling.workbook-skill-verify
    def test_row_count_measure_names_no_column(self):
        source = self.read_config(
            {"number_columns": [{"measure_name": "Invoices", "column_name": "count", "aggregation": "count"}]}
        )
        self.assertEqual(source, set())

    # @feature tooling.workbook-skill-verify
    def test_expression_measure_names_no_column(self):
        source = self.read_config(
            {
                "number_columns": [
                    {"measure_name": "Net", "expression": {"expression": "sum(debit) - sum(credit)"}}
                ]
            }
        )
        self.assertEqual(source, set())

    # @feature tooling.workbook-skill-verify
    def test_dimension_reads_its_column_whatever_its_name(self):
        source = self.read_config({"rows": [{"dimension_name": "Customer", "column_name": "customer"}]})
        self.assertEqual(source, {"customer"})

    # @feature tooling.workbook-skill-verify
    def test_misspelled_dimension_column_is_reported(self):
        """A column and a dimension name misspelled the same way must not cancel out."""
        source = self.read_config(
            {"x_axis": {"dimension": {"dimension_name": "postng", "column_name": "postng"}}}
        )
        self.assertEqual(source, {"postng"})

    # @feature tooling.workbook-skill-verify
    def test_order_by_names_are_not_source_columns(self):
        source = self.read_config(
            {
                "values": [{"measure_name": "Revenue", "column_name": "base_net_total"}],
                "order_by": [{"column": {"column_name": "Revenue"}}],
            }
        )
        self.assertEqual(source, {"base_net_total"})

    # @feature tooling.workbook-skill-verify
    def test_chart_filter_column_is_read(self):
        source = self.read_config(
            {
                "filters": {
                    "logical_operator": "And",
                    "filters": [{"column": {"column_name": "status"}, "operator": "=", "value": "Paid"}],
                }
            }
        )
        self.assertEqual(source, {"status"})


class TestSourceTables(unittest.TestCase):
    """`source_tables` finds the real tables a pipeline reads, for the data store check."""

    @classmethod
    def setUpClass(cls):
        cls.source_tables = staticmethod(load_template().source_tables)

    # @feature tooling.workbook-skill-verify
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

    # @feature tooling.workbook-skill-verify
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

    # @feature tooling.workbook-skill-verify
    def test_follows_references_transitively(self):
        self.assertEqual(self.query_chain("qA", self.operations), {"qA", "qB", "qC"})

    # @feature tooling.workbook-skill-verify
    def test_an_unrelated_query_is_not_in_the_chain(self):
        self.assertNotIn("qZ", self.query_chain("qA", self.operations))

    # @feature tooling.workbook-skill-verify
    def test_a_reference_cycle_terminates(self):
        operations = {
            "q1": [{"type": "source", "table": {"type": "query", "query_name": "q2"}}],
            "q2": [{"type": "source", "table": {"type": "query", "query_name": "q1"}}],
        }
        self.assertEqual(self.query_chain("q1", operations), {"q1", "q2"})


class TestDroppedSort(unittest.TestCase):
    """A chart drops a sort its result has no column for. That fails it only with a `limit`."""

    @classmethod
    def setUpClass(cls):
        cls.template = load_template()

    def chart(self, **entry):
        return {"charts": [{"name": "c1", "title": "Top", "rows": 3, **entry}]}

    def report(self, result):
        """The exit code, and what was printed."""
        out = io.StringIO()
        with redirect_stdout(out):
            return self.template.report(result), out.getvalue()

    # @feature tooling.workbook-skill-verify
    def test_a_sort_the_result_lacks_is_found(self):
        config = {"order_by": [{"column": {"column_name": "Revenue"}}, {"column": {"column_name": "region"}}]}
        self.assertEqual(self.template.unresolved_sorts(config, [{"name": "region"}]), ["Revenue"])

    # @feature tooling.workbook-skill-verify
    def test_a_dropped_sort_without_a_limit_is_a_warning(self):
        code, out = self.report(self.chart(ok=True, unresolved_order_by=["Revenue"]))
        self.assertEqual(code, 0)
        self.assertIn("warning: chart c1 (Top) sorts by ['Revenue']", out)

    # @feature tooling.workbook-skill-verify
    def test_a_dropped_sort_with_a_limit_fails_naming_the_sort(self):
        code, out = self.report(self.chart(ok=False, unresolved_order_by=["Revenue"]))
        self.assertEqual(code, 1)
        self.assertIn("- chart c1 (Top) sorts by ['Revenue']", out)


if __name__ == "__main__":
    unittest.main()
