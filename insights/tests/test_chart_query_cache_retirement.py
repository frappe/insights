"""The one-time removal of the query documents charts cached their query in.

A chart's query is derived from its config now, so the documents the browser
used to write it into are caches nothing fills or reads. The field is gone from
the doctype. The column it left behind is what the patch reads its way out by.
See `insights/patches/retire_chart_query_cache.py`.
"""

from unittest.mock import patch

import frappe

from insights.patches.retire_chart_query_cache import ALERT, CHART, EXECUTION_LOG, FIELD, QUERY, REFERENCE
from insights.patches.retire_chart_query_cache import execute as retire
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
)
from insights.upgrade import ITEM

OWNER = "Administrator"
ALERT_OWNER = "chart_query_cache_alert_owner@test.com"
WORKBOOK_TITLE = "Chart Query Cache Test Workbook"


class TestChartQueryCacheRetirement(InsightsIntegrationTestCase):
    SAVEPOINT = "test_chart_query_cache_retirement"

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name
        create_user(ALERT_OWNER, roles="Insights User")
        # a site installed on this release never had the field, so its column is
        # put back for the patch to read
        cls.added_column = FIELD not in frappe.db.get_table_columns(CHART)
        if cls.added_column:
            frappe.db.sql_ddl(f"alter table `tab{CHART}` add column `{FIELD}` varchar(140)")
            frappe.client_cache.delete_value(f"table_columns::tab{CHART}")

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True)
        delete_users(ALERT_OWNER)
        if cls.added_column:
            frappe.db.sql_ddl(f"alter table `tab{CHART}` drop column `{FIELD}`")
            frappe.client_cache.delete_value(f"table_columns::tab{CHART}")

    def before_test(self):
        frappe.db.delete(ITEM)

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

    # @feature upgrade.cached-queries-removed
    def test_a_cached_query_is_deleted(self):
        _chart, cache = self.cached_query()

        retire()

        self.assertFalse(frappe.db.exists(QUERY, cache))

    # @feature upgrade.cached-queries-removed
    def test_a_cache_is_deleted_without_a_job(self):
        """A site can hold thousands of caches, and a job per delete floods the
        queue the moment the patch commits."""
        _chart, cache = self.cached_query()

        with patch("frappe.enqueue") as enqueue:
            retire()

        self.assertFalse(frappe.db.exists(QUERY, cache))
        enqueue.assert_not_called()

    # @feature upgrade.cached-queries-removed
    def test_the_history_goes_with_the_cache(self):
        _chart, cache = self.cached_query()
        frappe.get_doc({"doctype": "Version", "ref_doctype": QUERY, "docname": cache, "data": "{}"}).insert(
            ignore_permissions=True
        )

        retire()

        self.assertFalse(frappe.db.exists("Version", {"ref_doctype": QUERY, "docname": cache}))

    # @feature upgrade.cached-queries-removed
    def test_a_cache_an_alert_watches_stays_as_a_query_and_its_owner_is_told(self):
        chart, cache = self.cached_query()
        alert = frappe.get_doc(
            {
                "doctype": ALERT,
                "title": "Chart Query Cache Test Alert",
                "query": cache,
                "condition": "count > 0",
            }
        )
        alert.db_insert()
        frappe.db.set_value(ALERT, alert.name, "owner", ALERT_OWNER)

        retire()

        self.assertTrue(frappe.db.exists(ALERT, alert.name))
        self.assertTrue(frappe.db.exists(QUERY, cache))
        self.assertEqual(
            frappe.db.sql_list(f"select `{FIELD}` from `tab{CHART}` where name = %s", chart), [None]
        )
        items = frappe.get_all(ITEM, filters={"code": "J1"}, fields=["reference_name", "user", "data"])
        self.assertEqual(
            [(item.reference_name, item.user, frappe.parse_json(item.data)) for item in items],
            [
                (
                    cache,
                    ALERT_OWNER,
                    {"alert": "Chart Query Cache Test Alert", "chart": "Chart Query Cache Test Chart"},
                )
            ],
        )

    # @feature upgrade.cached-queries-removed
    def test_a_charts_runs_are_logged_under_its_query_once_its_cache_is_gone(self):
        """The data store cleanup reads the logs to find tables nobody reads, and
        a log naming a deleted cache reads none."""
        chart, cache = self.cached_query()
        source = create_test_query(OWNER, self.workbook, title="Chart Query Cache Test Source")
        frappe.db.set_value(CHART, chart, "query", source.name)
        log = frappe.get_doc({"doctype": EXECUTION_LOG, "sql": "select 1", "query": cache}).insert()

        retire()

        self.assertEqual(frappe.db.get_value(EXECUTION_LOG, log.name, "query"), source.name)

    def queries_in_workbook(self):
        return frappe.get_all(QUERY, filters={"workbook": self.workbook}, pluck="name", order_by="name")

    # @feature upgrade.cached-queries-removed
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

    # @feature upgrade.cached-queries-removed
    def test_a_cache_a_chart_reads_is_kept(self):
        """No surface lists a cache in the query picker, so this should not
        happen — and the delete is permanent, so the chart's own field says so
        rather than the column nothing reads."""
        _chart, cache = self.cached_query()
        reader = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": "Chart Query Cache Test Reader",
                "workbook": self.workbook,
                "chart_type": "Bar",
                "query": cache,
                "config": {},
            }
        ).insert()

        retire()

        self.assertTrue(frappe.db.exists(QUERY, cache))
        self.assertEqual(frappe.db.get_value(DT.CHART, reader.name, "query"), cache)

    # @feature upgrade.cached-queries-removed
    def test_a_chart_reading_its_own_cache_reads_the_query_the_cache_read(self):
        """Its rows were the cache's: the source with the chart's config applied.
        Read from the cache, the config would summarize what is already summarized."""
        chart, cache = self.cached_query()
        source = create_test_query(OWNER, self.workbook, title="Chart Query Cache Test Source")
        operations = [
            {
                "type": "source",
                "table": {"type": "query", "workbook": self.workbook, "query_name": source.name},
            }
        ]
        frappe.db.set_value(QUERY, cache, "operations", frappe.as_json(operations))
        frappe.db.set_value(CHART, chart, "query", cache)

        retire()

        self.assertEqual(frappe.db.get_value(CHART, chart, "query"), source.name)
        self.assertFalse(frappe.db.exists(QUERY, cache))

    # @feature upgrade.cached-queries-removed
    def test_a_cache_another_query_sources_is_kept(self):
        """A cache a query reads is not a cache any more, and the delete is
        forced: it would take the reader's source with it."""
        _chart, cache = self.cached_query()
        reader = create_test_query(OWNER, self.workbook, title="Chart Query Cache Test Reader Query")
        frappe.get_doc(
            {
                "doctype": REFERENCE,
                "query": reader.name,
                "ref_type": "Query",
                "ref_query": cache,
            }
        ).insert()

        retire()

        self.assertTrue(frappe.db.exists(QUERY, cache))

    # @feature upgrade.cached-queries-removed
    def test_a_kept_cache_takes_its_charts_title(self):
        """A cache had no title of its own, and a kept one is listed with the
        workbook's queries."""
        _chart, cache = self.cached_query()
        frappe.db.set_value(QUERY, cache, "title", None)
        reader = create_test_query(OWNER, self.workbook, title="Chart Query Cache Test Reader Query")
        frappe.get_doc(
            {"doctype": REFERENCE, "query": reader.name, "ref_type": "Query", "ref_query": cache}
        ).insert()

        retire()

        self.assertEqual(frappe.db.get_value(QUERY, cache, "title"), "Chart Query Cache Test Chart")

    # @feature upgrade.cached-queries-removed
    def test_a_query_no_chart_cached_is_left_alone(self):
        mine = create_test_query(OWNER, self.workbook, title="Chart Query Cache Test Own Query")

        retire()

        self.assertTrue(frappe.db.exists(QUERY, mine.name))
