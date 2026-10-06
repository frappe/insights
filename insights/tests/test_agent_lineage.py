"""What the agent lineage endpoint reports about a query, and to whom."""

import frappe
from frappe.utils import get_datetime

from insights.api.ai.lineage import describe_query
from insights.api.workbooks import update_share_permissions
from insights.insights.query_utils import downstream_queries, sync_query_references
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
    create_test_query,
    create_test_workbook,
)
from insights.tests.permissions_utils import (
    TEST_DS,
    TEST_TABLE1,
    USER_1,
    USER_2,
    cleanup_test_fixtures,
    create_test_data_sources,
    create_test_tables,
    create_test_users,
)

OWNER = USER_1
READER = USER_2
SYNC_FROM = get_datetime("2026-01-01 00:00:00")


def table(name):
    return {"type": "table", "data_source": TEST_DS, "table_name": name}


def query_table(name):
    return {"type": "query", "workbook": 0, "query_name": name}


def set_operations(query, operations):
    """Write operations past the save that refuses them, and the edges a save would have made."""
    frappe.db.set_value(DT.QUERY, query, "operations", frappe.as_json(operations))
    sync_query_references(query, operations)


def source(of):
    return {"type": "source", "table": of}


def join(of):
    return {
        "type": "join",
        "join_type": "left",
        "table": of,
        "join_condition": {
            "left_column": {"type": "column", "column_name": "id"},
            "right_column": {"type": "column", "column_name": "id"},
        },
        "select_columns": [{"type": "column", "column_name": "id"}],
    }


class TestAgentLineage(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cleanup_test_fixtures()
        create_test_users()
        create_test_data_sources()
        create_test_tables()
        frappe.db.set_value(DT.TABLE, TEST_TABLE1, {"stored": 1, "row_limit": 1000, "sync_from": SYNC_FROM})

        cls.workbook = create_test_workbook(OWNER, title="Agent Lineage Workbook").name
        cls.base = cls.query("Base", [source(table("table1"))])
        cls.middle = cls.query("Middle", [source(query_table(cls.base)), join(table("table2"))])
        cls.top = cls.query("Top", [source(table("table3")), join(query_table(cls.middle))])
        cls.unrelated = cls.query("Unrelated", [source(table("table1"))])

        cls.chart = create_test_chart(OWNER, cls.workbook, query=cls.top, title="Top Chart").name
        cls.off_board_chart = create_test_chart(
            OWNER, cls.workbook, query=cls.top, title="Off Board Chart"
        ).name
        cls.dashboard = cls.make_dashboard()

        # a workbook the reader is not shared into, holding a query that reads
        # the base query, as a reference saved before sources were kept in
        # their own workbook
        cls.private_workbook = create_test_workbook(OWNER, title="Agent Lineage Private").name
        cls.hidden = cls.query("Hidden", [source(table("table1"))], workbook=cls.private_workbook)
        set_operations(cls.hidden, [source(query_table(cls.base))])
        cls.hidden_chart = create_test_chart(
            OWNER, cls.private_workbook, query=cls.hidden, title="Hidden Chart"
        ).name
        # readable, but reached only through the hidden query
        cls.beyond = cls.query("Beyond", [source(table("table1"))])
        set_operations(cls.beyond, [source(query_table(cls.hidden))])

        with as_user(OWNER):
            update_share_permissions(cls.workbook, [{"user": READER, "read": 1, "write": 0}])

    @classmethod
    def after_class(cls):
        cleanup_test_fixtures()

    @classmethod
    def query(cls, title, operations, workbook=None):
        return create_test_query(
            OWNER, workbook or cls.workbook, title=f"Agent Lineage {title}", operations=operations
        ).name

    @classmethod
    def make_dashboard(cls):
        def link(query, column="id"):
            return f"`{query}`.`{column}`"

        with as_user(OWNER):
            return (
                frappe.get_doc(
                    {
                        "doctype": DT.DASHBOARD,
                        "title": "Agent Lineage Dashboard",
                        "workbook": cls.workbook,
                        "items": [
                            {
                                "type": "chart",
                                "chart": cls.chart,
                                "layout": {"i": "chart-1", "x": 0, "y": 1, "w": 10, "h": 8},
                            },
                            {
                                "type": "filter",
                                "filter_name": "Base Id",
                                "filter_type": "String",
                                "links": {
                                    cls.chart: link(cls.base),
                                    # not on the dashboard, so the link filters nothing
                                    cls.off_board_chart: link(cls.base),
                                },
                                "layout": {"i": "filter-1", "x": 0, "y": 0, "w": 4, "h": 1},
                            },
                            {
                                "type": "filter",
                                "filter_name": "Unrelated Id",
                                "filter_type": "String",
                                # the chart does not read this query, so the link filters nothing
                                "links": {cls.chart: link(cls.unrelated)},
                                "layout": {"i": "filter-2", "x": 4, "y": 0, "w": 4, "h": 1},
                            },
                        ],
                    }
                )
                .insert()
                .name
            )

    def describe(self, user, query):
        with self.as_user(user):
            return describe_query(query)

    # @feature tooling.query-lineage
    def test_upstream_names_every_query_and_table_the_query_reads_through_every_hop(self):
        lineage = self.describe(OWNER, self.top)

        self.assertEqual(lineage["name"], self.top)
        self.assertEqual(lineage["workbook"], self.workbook)
        self.assertEqual(lineage["title"], "Agent Lineage Top")
        self.assertTrue(lineage["use_live_connection"])
        self.assertEqual(lineage["operations"], ["source", "join"])
        self.assertEqual(lineage["reads"], [self.middle])

        upstream = lineage["upstream"]
        self.assertEqual([query["name"] for query in upstream["queries"]], [self.middle, self.base])
        self.assertEqual(upstream["queries"][0]["reads"], [self.base])

        tables = {table["table_name"]: table for table in upstream["tables"]}
        self.assertEqual(set(tables), {"table1", "table2", "table3"})
        self.assertEqual(
            tables["table1"],
            {
                "data_source": TEST_DS,
                "table_name": "table1",
                "stored": True,
                "row_limit": 1000,
                "sync_from": SYNC_FROM,
                "read_by": [self.base],
            },
        )
        self.assertFalse(tables["table3"]["stored"])
        self.assertEqual(tables["table3"]["read_by"], [self.top])

    # @feature tooling.query-lineage
    def test_downstream_names_the_queries_charts_dashboards_and_filter_links_that_read_the_query(self):
        downstream = self.describe(OWNER, self.base)["downstream"]

        order = [query["name"] for query in downstream["queries"]]
        self.assertEqual(set(order), {self.middle, self.top, self.hidden, self.beyond})
        # nearest first: the top query reads the base query through the middle one
        self.assertLess(order.index(self.middle), order.index(self.top))
        self.assertLess(order.index(self.hidden), order.index(self.beyond))
        self.assertEqual(
            {chart["name"] for chart in downstream["charts"]},
            {self.chart, self.off_board_chart, self.hidden_chart},
        )
        self.assertEqual(
            downstream["dashboards"],
            [
                {
                    "name": self.dashboard,
                    "title": "Agent Lineage Dashboard",
                    "workbook": self.workbook,
                    "charts": [self.chart],
                }
            ],
        )
        self.assertEqual(
            downstream["filter_links"],
            [
                {
                    "dashboard": self.dashboard,
                    "filter_name": "Base Id",
                    "chart": self.chart,
                    "query": self.base,
                    "column": "id",
                }
            ],
        )

    # @feature tooling.query-lineage permissions.lineage-respects-access
    def test_lineage_names_what_the_caller_may_read_and_walks_through_nothing_else(self):
        reader = self.describe(READER, self.base)["downstream"]

        self.assertEqual([query["name"] for query in reader["queries"]], [self.middle, self.top])
        self.assertEqual({chart["name"] for chart in reader["charts"]}, {self.chart, self.off_board_chart})

        # the beyond query reads a query the reader may not read, and does not name it
        beyond = self.describe(READER, self.beyond)
        self.assertEqual(beyond["reads"], [])
        self.assertEqual(beyond["upstream"]["queries"], [])

    # @feature permissions.lineage-respects-access
    def test_a_downstream_walk_needs_the_callers_read_filter(self):
        with self.assertRaises(TypeError):
            downstream_queries(self.base)

    # @feature permissions.lineage-respects-access permissions.denied-is-not-found
    def test_a_query_the_caller_may_not_read_is_not_found(self):
        with self.assertRaises(frappe.DoesNotExistError):
            self.describe(READER, self.hidden)

    # @feature tooling.query-lineage
    def test_a_reference_cycle_ends_the_walk(self):
        first = self.query("Cycle First", [source(table("table1"))])
        second = self.query("Cycle Second", [source(query_table(first))])
        set_operations(first, [source(query_table(second))])

        lineage = self.describe(OWNER, first)

        self.assertEqual([query["name"] for query in lineage["upstream"]["queries"]], [second])
        self.assertEqual([query["name"] for query in lineage["downstream"]["queries"]], [second])

    # @feature tooling.query-lineage
    def test_downstream_reads_the_reference_table_so_it_lags_the_job_that_rebuilds_it(self):
        pending = self.query("Pending", [source(table("table1"))])
        frappe.db.set_value(
            DT.QUERY, pending, "operations", frappe.as_json([source(query_table(self.unrelated))])
        )

        self.assertEqual(self.describe(OWNER, self.unrelated)["downstream"]["queries"], [])

        sync_query_references(pending, [source(query_table(self.unrelated))])
        self.assertEqual(
            [q["name"] for q in self.describe(OWNER, self.unrelated)["downstream"]["queries"]], [pending]
        )
