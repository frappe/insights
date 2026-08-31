from unittest.mock import patch

import frappe

from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
    get_code_results,
    resolve_variables,
)
from insights.tests.base import InsightsIntegrationTestCase


class TestScriptQueryLogs(InsightsIntegrationTestCase):
    def run_code(self, code):
        published = []
        with patch(
            "frappe.publish_realtime",
            side_effect=lambda **kwargs: published.append(kwargs),
        ):
            try:
                results = get_code_results(code, variables={"token": "secret"})
            except Exception as e:
                return published, e
            return published, results

    def get_logs(self, published):
        events = [p for p in published if p.get("event") == "insights_script_log"]
        self.assertEqual(len(events), 1)
        return events[0]["message"]["logs"]

    def test_error_is_logged_with_line_number(self):
        code = "\n".join(
            [
                "rows = [{'a': 1}]",
                "results = rows[5]",
            ]
        )
        published, error = self.run_code(code)

        self.assertIsInstance(error, IndexError)
        logs = self.get_logs(published)
        self.assertIn("Line 2: results = rows[5]", logs[-1])
        self.assertIn("IndexError", logs[-1])

    def test_syntax_error_is_logged(self):
        published, error = self.run_code("results = [")

        self.assertIsInstance(error, SyntaxError)
        logs = self.get_logs(published)
        self.assertIn("SyntaxError", logs[-1])

    def test_prints_before_the_error_survive(self):
        code = "\n".join(
            [
                "print('step one')",
                "raise ValueError('boom')",
            ]
        )
        published, error = self.run_code(code)

        self.assertIsInstance(error, ValueError)
        logs = self.get_logs(published)
        self.assertEqual(logs[0], "step one")
        self.assertIn("ValueError: boom", logs[-1])

    def test_logs_are_published_on_success(self):
        code = "\n".join(
            [
                "print('done')",
                "results = [{'a': 1}]",
            ]
        )
        published, results = self.run_code(code)

        self.assertEqual(len(results), 1)
        logs = self.get_logs(published)
        self.assertEqual(logs[0], "done")
        self.assertRegex(logs[-1], r"^1 rows in [\d.]+s$")

    def test_empty_results_give_an_empty_table(self):
        published, results = self.run_code("results = []")

        self.assertEqual(list(results.columns), ["results"])
        self.assertEqual(len(results), 0)
        self.assertRegex(self.get_logs(published)[-1], r"^0 rows in [\d.]+s$")

    def test_variables_reach_the_script(self):
        _published, results = self.run_code("results = [{'a': token}]")

        self.assertEqual(results["a"].tolist(), ["secret"])

    def test_resolve_variables_reads_plain_dicts(self):
        variables = [{"variable_name": "token", "variable_value": "secret"}]
        self.assertEqual(resolve_variables(variables), {"token": "secret"})
        self.assertEqual(resolve_variables(None), {})


class TestScriptQueryCache(InsightsIntegrationTestCase):
    def build(self, code, variables=None, force=False):
        doc = frappe._dict(
            name="Script Query Cache Test",
            title="Script Query Cache Test",
            use_live_connection=0,
            variables=variables,
            operations=frappe.as_json([{"type": "code", "code": code}]),
        )
        builder = IbisQueryBuilder(doc)
        builder.force = force
        return builder.build()

    def test_empty_results_build_a_queryable_table(self):
        result = self.build("results = []").execute()

        self.assertEqual(list(result.columns), ["results"])
        self.assertEqual(len(result), 0)

    def test_a_variable_change_reruns_the_script(self):
        code = "results = [{'a': token}]"

        first = self.build(code, variables=[{"variable_name": "token", "variable_value": "one"}])
        self.assertEqual(first.execute()["a"].tolist(), ["one"])

        second = self.build(code, variables=[{"variable_name": "token", "variable_value": "two"}])
        self.assertEqual(second.execute()["a"].tolist(), ["two"])

    def test_force_skips_the_code_cache(self):
        code = "import_count = frappe.db.count('DocType')\nresults = [{'a': import_count}]"

        with patch(
            "insights.insights.doctype.insights_data_source_v3.ibis_utils.get_code_results",
            wraps=get_code_results,
        ) as spy:
            self.build(code).execute()
            self.build(code).execute()
            self.assertEqual(spy.call_count, 1)

            self.build(code, force=True).execute()
            self.assertEqual(spy.call_count, 2)
