# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
"""An expression describes a query, so it reaches no path, URL or backend.

`get_functions()` builds the context an expression evaluates in. Several ibis
top-level names are readers and writers, and the objects the context hands out
carry output methods of their own, so the boundary is easy to widen by accident.

The rule is held here rather than a list of names, so an ibis upgrade that adds
a reader does not quietly become reachable.
"""

import os
import tempfile

import frappe
import ibis
from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_data_source_v3.ibis.utils import get_functions
from insights.insights.doctype.insights_data_source_v3.ibis_utils import exec_with_return


class TestExpressionIsolation(UnitTestCase):
    def evaluate(self, expression):
        return exec_with_return(expression, dict(get_functions()))

    def assert_refused(self, expression):
        with self.assertRaises(frappe.PermissionError):
            self.evaluate(expression)

    # --- the rule covers what ibis actually ships ---

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

    # --- the readers and writers themselves ---

    def test_a_reader_is_refused(self):
        self.assert_refused("ibis.read_csv('/tmp/does-not-matter.csv')")
        self.assert_refused("ibis.read_json('/tmp/does-not-matter.csv')")
        self.assert_refused("ibis.read_parquet('/tmp/does-not-matter.csv')")
        self.assert_refused("ibis.read_delta('/tmp/does-not-matter.csv')")

    def test_a_reader_given_a_url_is_refused(self):
        self.assert_refused("ibis.read_csv('http://example.invalid/x.csv')")

    def test_a_writer_is_refused(self):
        """The context carries table and column objects, so an output method on
        one of them is as reachable as a top-level name."""
        target = os.path.join(tempfile.gettempdir(), "insights_expression_io_test.csv")
        if os.path.exists(target):
            os.remove(target)
        self.assert_refused(f"ibis.memtable({{'a': [1, 2]}}).to_csv({target!r})")
        self.assertFalse(os.path.exists(target))

    def test_the_rule_holds_for_a_multi_statement_script(self):
        """A single expression takes the safe_eval branch, several take safe_exec."""
        self.assert_refused("path = '/tmp/does-not-matter.csv'\nibis.read_csv(path)")

    # --- the legitimate path still works ---

    def test_pure_expressions_still_evaluate(self):
        self.assertIsNotNone(self.evaluate("ibis.literal(1) + 1"))
        self.assertIsNotNone(self.evaluate("ibis.ifelse(ibis.literal(True), 1, 2)"))
        self.assertIsNotNone(self.evaluate("ibis.coalesce(ibis.null(), ibis.literal(2))"))
