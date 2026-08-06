"""Does the server derive the query the browser used to derive?

A temporary seam. The browser's derivation is the oracle and its output was
persisted, chart by chart, in the shipped workbooks — so every shipped chart is
a case the two derivations must agree on. The seam goes away with the cached
queries: once nothing persists a derived query there is nothing left to diff.

Read `insights/insights/doctype/insights_chart_v3/chart_query.py` for what is
being derived, and `frontend/src2/charts/chart.ts` for what it was ported from.
"""

import json
import unittest
from pathlib import Path

import insights
from insights.insights.doctype.insights_chart_v3.chart_query import config_errors, derive_operations
from insights.tests.factories import chart_derivation_fixtures

BUNDLES = Path(insights.__file__).parent / "insights"


def shipped_charts():
    """Every shipped chart, paired with the derived query the browser left behind."""
    for chart_file in sorted(BUNDLES.glob("erpnext_*/chart/*.json")):
        chart = json.loads(chart_file.read_text())
        cache = chart_file.parent.parent / "query" / f"{chart['data_query']}.json"
        yield chart_file.stem, chart, json.loads(cache.read_text())["operations"]


def comparable(operations):
    """The operations, minus what says nothing about the query that runs.

    The shipped format rewrites the workbook on every reference to a placeholder,
    because a shipped file has no workbook until it is imported. A query name is
    unique on the site and is what resolves the reference, so the placeholder is
    all the comparison can ask for.
    """
    operations = json.loads(json.dumps(operations))
    for operation in operations:
        table = operation.get("table") or {}
        if "workbook" in table:
            table["workbook"] = 0
    return operations


class TestChartQueryParity(unittest.TestCase):
    def assert_derives(self, case, chart, expected):
        with self.subTest(chart=case):
            self.assertEqual(
                config_errors(chart["chart_type"], chart["query"], chart["config"]),
                [],
                f"{case} is shipped, so its config must be drawable",
            )
            derived = derive_operations(chart["chart_type"], chart["query"], chart["config"])
            self.assertEqual(comparable(derived), comparable(expected))

    def test_every_shipped_chart_derives_the_query_it_ships_with(self):
        cases = list(shipped_charts())
        self.assertTrue(cases, "no shipped charts found to check against")

        for case, chart, operations in cases:
            self.assert_derives(case, chart, operations)

    def test_the_shapes_no_shipped_chart_uses_derive_too(self):
        for fixture in chart_derivation_fixtures():
            self.assert_derives(fixture["title"], fixture, fixture["operations"])

    def test_every_chart_type_is_covered(self):
        """The port is only checked where a case exists, so count the types."""
        covered = {chart["chart_type"] for _, chart, _ in shipped_charts()}
        covered |= {fixture["chart_type"] for fixture in chart_derivation_fixtures()}

        self.assertEqual(
            covered,
            {"Bar", "Line", "Row", "Number", "Donut", "Funnel", "Table", "Map", "Bubble"},
        )

    def test_a_config_that_names_no_columns_cannot_be_drawn(self):
        for chart_type in ("Bar", "Number", "Donut", "Funnel", "Table", "Map", "Bubble"):
            with self.subTest(chart_type=chart_type):
                self.assertTrue(config_errors(chart_type, "some-query", {}))

        self.assertTrue(config_errors("Bar", "", {}), "a chart with no source query")
        self.assertTrue(config_errors("Treemap", "some-query", {}), "an unknown chart type")
