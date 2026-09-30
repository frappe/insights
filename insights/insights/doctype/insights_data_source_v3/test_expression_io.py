# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
"""An expression describes a query, so it reaches no path, URL or backend.

`get_functions()` builds the context an expression evaluates in. Several ibis
top-level names are readers and writers, and the objects the context hands out
have output methods of their own, so the boundary is easy to widen by accident.

The rule is held here rather than a list of names, so an ibis upgrade that adds
a reader does not quietly become reachable.
"""

import datetime
import os
import tempfile

import frappe
import ibis
from frappe.tests import UnitTestCase

from insights.exceptions import ExpressionSyntaxError
from insights.insights.doctype.insights_data_source_v3.ibis.utils import get_functions
from insights.insights.doctype.insights_data_source_v3.ibis_utils import exec_with_return


def refused_ibis_names() -> list[str]:
    from insights.insights.doctype.insights_data_source_v3.ibis.utils import (
        ibis_attribute_names,
        is_refused_in_expression,
    )

    names = sorted(name for name in ibis_attribute_names() if is_refused_in_expression(name))
    assert names, "expected ibis to define I/O, backend and run names"
    return names


class TestExpressionIsolation(UnitTestCase):
    def evaluate(self, expression):
        """`q` is the relation in hand, as `IbisQueryBuilder.evaluate_expression` passes it."""
        return exec_with_return(expression, {**get_functions(), "q": ibis.memtable({"a": [1, 2]})})

    def assert_refused(self, expression):
        with self.assertRaises(frappe.PermissionError):
            self.evaluate(expression)

    # --- the rule covers what ibis actually ships ---

    # @feature query.expression-cannot-reach-files
    def test_the_rule_covers_every_io_name_ibis_exports(self):
        """The rule, not the names: an ibis upgrade must not need an edit here."""
        from insights.insights.doctype.insights_data_source_v3.ibis.utils import is_io_attribute

        io_names = [
            name
            for name in dir(ibis)
            if not name.startswith("_")
            and (name.startswith(("read_", "to_", "from_")) or name in ("connect", "set_backend"))
        ]
        self.assertTrue(io_names, "expected ibis to export some I/O names")
        for name in io_names:
            self.assertTrue(is_io_attribute(name), f"{name} is I/O but the rule allows it")

    # @feature query.expression-cannot-reach-files
    def test_no_io_name_is_reachable_from_the_context(self):
        """Every namespace an expression reaches by attribute must be clean.

        The rule is attribute-only on purpose, so the flat names are not checked:
        `to_inr(amount)` is a call on a plain name and stays legal.
        """
        from insights.insights.doctype.insights_data_source_v3.ibis.utils import is_io_attribute

        context = get_functions()
        namespaces = {"ibis": context.ibis, "s": context.s, "selectors": context.selectors}
        for namespace, names in namespaces.items():
            for name in names:
                self.assertFalse(is_io_attribute(name), f"{namespace}.{name} is exposed to expressions")

    # @feature query.expression-cannot-reach-files
    def test_no_pandas_numpy_or_module_value_is_reachable_from_the_context(self):
        """The source check lets an I/O name through as a column of a table in
        hand, which is safe only while no object other than ibis's is reachable:
        a pandas `to_pickle` or a numpy `tofile` is not an ibis name."""
        import types

        from insights.insights.doctype.insights_data_source_v3.sandbox import expression_globals

        def walk(value, path, depth=0):
            modules = {getattr(value, "__module__", None) or "", type(value).__module__}
            self.assertFalse(isinstance(value, types.ModuleType), f"{path} is a module")
            self.assertFalse(
                {module.partition(".")[0] for module in modules} & {"pandas", "numpy"},
                f"{path} is a pandas or numpy object",
            )
            if isinstance(value, dict) and depth < 3:
                for key, item in value.items():
                    walk(item, f"{path}.{key}", depth + 1)

        for name, value in {**get_functions(), **expression_globals()}.items():
            walk(value, name)

    # @feature query.expression-column-named-like-io
    def test_the_refusal_names_the_table_that_holds_the_column(self):
        q = ibis.memtable({"a": [1]})
        other = ibis.memtable({"source": ["s"]})
        for context, expression, hint in (
            ({"q": q, "t1": q, "t2": other}, "t1.a == t2.source", "t2['source']"),
            ({"table": other}, "table.source", "table['source']"),
        ):
            with self.subTest(expression=expression), self.assertRaises(frappe.PermissionError) as refusal:
                exec_with_return(expression, {**get_functions(), **context})
            self.assertIn(f"Read the column as {hint}", str(refusal.exception))

    # @feature query.expression-cannot-reach-files
    def test_every_io_backend_and_run_name_ibis_defines_is_refused(self):
        """Enumerated from ibis, so a release that adds a name is tested with it."""
        for name in refused_ibis_names():
            for expression in (f"q.{name}", f"t = q.{name}\nt"):
                with self.subTest(expression=expression):
                    self.assert_refused(expression)

    # @feature query.expression-cannot-reach-files
    def test_no_name_ibis_defines_passes_as_a_column_of_that_name(self):
        """The source check lets an I/O name through when it is a column of a
        table in hand. That is safe only while no name ibis defines passes."""
        names = refused_ibis_names()
        q = ibis.memtable({name: [1] for name in names})
        for name in names:
            for expression in (f"q.{name}", f"t = q.{name}\nt"):
                with self.subTest(expression=expression), self.assertRaises(frappe.PermissionError):
                    exec_with_return(expression, {**get_functions(), "q": q})

    # --- the readers and writers themselves ---

    # @feature query.expression-cannot-reach-files
    def test_a_reader_is_refused(self):
        self.assert_refused("ibis.read_csv('/tmp/does-not-matter.csv')")
        self.assert_refused("ibis.read_json('/tmp/does-not-matter.csv')")
        self.assert_refused("ibis.read_parquet('/tmp/does-not-matter.csv')")
        self.assert_refused("ibis.read_delta('/tmp/does-not-matter.csv')")

    # @feature query.expression-cannot-reach-files
    def test_a_reader_given_a_url_is_refused(self):
        self.assert_refused("ibis.read_csv('http://example.invalid/x.csv')")

    # @feature query.expression-cannot-reach-files
    def test_a_writer_is_refused(self):
        """The context holds table and column objects, so an output method on
        one of them is as reachable as a top-level name."""
        target = os.path.join(tempfile.gettempdir(), "insights_expression_io_test.csv")
        if os.path.exists(target):
            os.remove(target)
        self.assert_refused(f"q.to_csv({target!r})")
        self.assertFalse(os.path.exists(target))

    # @feature query.expression-cannot-reach-files
    def test_a_column_named_like_a_table_method_is_a_column(self):
        """A table's method outranks its column on attribute access, so a bare
        column read by attribute would be the bound method."""
        from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder

        target = os.path.join(tempfile.gettempdir(), "insights_expression_column_test.csv")
        for name in ("to_csv", "sql", "execute"):
            with self.subTest(name=name):
                if os.path.exists(target):
                    os.remove(target)
                builder = IbisQueryBuilder(frappe._dict(name="t", operations="[]", use_live_connection=0))
                builder.query = ibis.memtable({name: ["x"]})

                self.assertEqual(
                    builder.evaluate_expression(f"{name}.length()").get_name(), f"StringLength({name})"
                )
                with self.assertRaises(ExpressionSyntaxError):
                    builder.evaluate_expression(f"{name}({target!r})")
                self.assertFalse(os.path.exists(target))

    # @feature query.expression-cannot-reach-files
    def test_functions_read_a_column_named_like_a_table_method_as_a_column(self):
        from insights.insights.doctype.insights_data_source_v3.ibis.functions import count, get_retention_data

        previous = frappe.flags.current_ibis_query
        self.addCleanup(setattr, frappe.flags, "current_ibis_query", previous)
        frappe.flags.current_ibis_query = ibis.memtable(
            {"execute": [datetime.date(2026, 1, 1), datetime.date(2026, 1, 2)], "sql": ["u1", "u1"]}
        )

        self.assertEqual(count().op().arg.name, "execute")
        retention = get_retention_data("execute", "sql", "day")
        self.assertIn("retention", retention.columns)

    # @feature query.expression-cannot-reach-files
    def test_the_rule_holds_for_a_multi_statement_script(self):
        """A single expression takes the safe_eval branch, several take safe_exec."""
        self.assert_refused("written = q.to_csv('/tmp/does-not-matter.csv')\nwritten")

    # @feature query.expression-cannot-reach-files
    def test_nothing_reaches_the_connection_or_runs_the_query(self):
        """`op()` leads to the backend a relation runs on; the rest run or compile
        the query in hand, which an expression only describes."""
        for name in (
            "op",
            "source",
            "raw_sql",
            "con",
            "execute",
            "compile",
            "cache",
            "preview",
            "release",
            "visualize",
        ):
            for expression in (
                f"q.{name}()",
                f"t = q.{name}()\nt",
            ):
                with self.subTest(name=name, expression=expression):
                    self.assert_refused(expression)

    # @feature query.expression-cannot-reach-files
    def test_no_plain_name_runs_sql(self):
        """A plain `sql(...)` would run `Table.sql` with no attribute for the
        source check to see."""
        from insights.insights.doctype.insights_data_source_v3.ibis.utils import get_function_list

        self.assertNotIn("sql", get_function_list())
        for expression in ("sql('select 1')", "query = 'select 1'\nsql(query)"):
            with self.subTest(expression=expression), self.assertRaises(NameError):
                self.evaluate(expression)

    # @feature query.expression-column-named-like-io
    def test_a_column_named_like_io_passes_only_on_its_table(self):
        """The rule was once on the name alone, so `t2.from_plan` was refused."""
        q = ibis.memtable({"a": [1], "from_plan": ["x"], "to_parquet": ["y"]})

        def evaluate(expression):
            return exec_with_return(expression, {**get_functions(), "q": q})

        self.assertEqual(evaluate("q.from_plan").get_name(), "from_plan")
        self.assertEqual(evaluate("plan = q.from_plan\nplan").get_name(), "from_plan")
        for expression in (
            "q.to_parquet('/tmp/does-not-matter.parquet')",
            "written = q.to_parquet('/tmp/does-not-matter.parquet')\nwritten",
        ):
            with self.subTest(expression=expression), self.assertRaises(frappe.PermissionError):
                evaluate(expression)

    # --- the legitimate path still works ---

    # @feature query.expression-cannot-reach-files
    def test_pure_expressions_still_evaluate(self):
        self.assertIsNotNone(self.evaluate("ibis.literal(1) + 1"))
        self.assertIsNotNone(self.evaluate("ibis.ifelse(ibis.literal(True), 1, 2)"))
        self.assertIsNotNone(self.evaluate("ibis.coalesce(ibis.null(), ibis.literal(2))"))
