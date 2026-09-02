"""The one-time removal of the query documents charts cached their query in.

A chart's query is derived from its config now, so the documents the browser
used to write it into are caches nothing fills or reads. The field is gone from
the doctype; the column it left behind is what the patch reads its way out by.
See `insights/patches/retire_chart_query_cache.py`.
"""

import frappe

from insights.patches.retire_chart_query_cache import CHART, FIELD, QUERY
from insights.patches.retire_chart_query_cache import execute as retire
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_query, create_test_workbook

OWNER = "Administrator"
WORKBOOK_TITLE = "Chart Query Cache Test Workbook"


class TestChartQueryCacheRetirement(InsightsIntegrationTestCase):
    SAVEPOINT = "test_chart_query_cache_retirement"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True)

    def before_test(self):
        if FIELD not in frappe.db.get_table_columns(CHART):
            self.skipTest(f"{CHART}.{FIELD} has been trimmed off this site, so there is nothing to read")

    def cached_query(self):
        """A chart and the query document it used to cache its rows' query in.

        The link is written the way the patch reads it: straight at the column,
        which is all that is left of the field.
        """
        query = create_test_query(OWNER, self.workbook, title="Chart Query Cache Test Query")
        chart = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": "Chart Query Cache Test Chart",
                "workbook": self.workbook,
                "chart_type": "Bar",
                "config": {},
            }
        ).insert()
        frappe.db.sql(f"update `tab{CHART}` set `{FIELD}` = %s where name = %s", (query.name, chart.name))
        return chart.name, query.name

    def test_a_cached_query_is_deleted(self):
        _chart, cache = self.cached_query()

        retire()

        self.assertFalse(frappe.db.exists(QUERY, cache))

    def queries_in_workbook(self):
        return frappe.get_all(QUERY, filters={"workbook": self.workbook}, pluck="name", order_by="name")

    def test_a_second_run_deletes_nothing(self):
        chart, cache = self.cached_query()
        mine = create_test_query(OWNER, self.workbook, title="Chart Query Cache Test Survivor")

        retire()
        once = self.queries_in_workbook()
        retire()

        self.assertEqual(self.queries_in_workbook(), once)
        self.assertNotIn(cache, once)
        self.assertIn(mine.name, once)
        # the chart still names the cache in the column nothing reads any more,
        # so the second run walks the same list and finds the document gone
        self.assertEqual(
            frappe.db.sql_list(f"select `{FIELD}` from `tab{CHART}` where name = %s", chart), [cache]
        )

    def test_a_query_no_chart_cached_is_left_alone(self):
        mine = create_test_query(OWNER, self.workbook, title="Chart Query Cache Test Own Query")

        retire()

        self.assertTrue(frappe.db.exists(QUERY, mine.name))
