"""Expressions from Insights 3 that read a column named like a backend attribute.

See `insights/patches/rewrite_backend_attribute_names.py`.
"""

import frappe
import ibis

from insights.insights.doctype.insights_data_source_v3.ibis.utils import get_functions
from insights.insights.doctype.insights_data_source_v3.ibis_utils import exec_with_return
from insights.patches.rewrite_backend_attribute_names import as_item_reads
from insights.patches.rewrite_backend_attribute_names import execute as rewrite
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_query, create_test_workbook
from insights.upgrade import ITEM

OWNER = "Administrator"
PREFIX = "Backend Attribute Rewrite Test"


def mutate(expression):
    return {
        "type": "mutate",
        "new_name": "result",
        "data_type": "String",
        "expression": {"type": "expression", "expression": expression},
    }


class TestBackendAttributeRewrite(InsightsIntegrationTestCase):
    SAVEPOINT = "test_backend_attribute_rewrite"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=PREFIX).name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)

    # @feature upgrade.expression-column-reads
    def test_a_column_read_by_attribute_is_read_by_item_and_runs(self):
        expression = "(\n    t1.lead == t2.source  # same lead\n    & t2.con.notnull()\n)"

        rewritten = as_item_reads(expression)

        self.assertEqual(
            rewritten, "(\n    t1.lead == t2['source']  # same lead\n    & t2['con'].notnull()\n)"
        )
        q = ibis.memtable({"lead": ["s"]})
        other = ibis.memtable({"source": ["s"]})
        exec_with_return("t1.lead == t2['source']", {**get_functions(), "t1": q, "t2": other})

    # @feature upgrade.expression-column-reads
    def test_a_method_call_is_left_as_written(self):
        for expression in ("q.cache()", "q.op()", "lower(source)", "q.source("):
            with self.subTest(expression=expression):
                self.assertEqual(as_item_reads(expression), expression)

    # @feature upgrade.expression-column-reads
    def test_the_patch_rewrites_a_stored_query_and_reports_a_method_it_cannot(self):
        frappe.db.delete(ITEM)
        source = {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
        }
        kept = create_test_query(OWNER, self.workbook, f"{PREFIX} Lead source", [source]).name
        called = create_test_query(OWNER, self.workbook, f"{PREFIX} Executes", [source]).name
        for query, expression in ((kept, "q.source"), (called, "q.execute()")):
            frappe.db.set_value(
                DT.QUERY,
                query,
                "operations",
                frappe.as_json([source, mutate(expression)]),
                update_modified=False,
            )

        rewrite()

        operations = frappe.parse_json(frappe.db.get_value(DT.QUERY, kept, "operations"))
        self.assertEqual(operations[1]["expression"]["expression"], "q['source']")
        self.assertFalse(frappe.db.exists(ITEM, {"code": "Q5", "reference_name": kept}))
        message, data = frappe.db.get_value(
            ITEM, {"code": "Q5", "reference_name": called}, ["message", "data"]
        )
        self.assertIn("`execute`", message)
        self.assertEqual(
            frappe.parse_json(data), {"title": f"{PREFIX} Executes", "names": ["execute"], "kind": "query"}
        )
