"""What `verify_workbook` reports about a workbook an agent authored.

Each fault here saved cleanly and failed only when a reader opened the
dashboard, which is what agents checked by hand before this endpoint.
"""

from unittest.mock import patch

import frappe

from insights.api.ai.verify import error_message, verify_workbook
from insights.insights.doctype.insights_data_source_v3.data_warehouse import WarehouseTable
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_query_v3.insights_query_v3 import InsightsQueryv3
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
    delete_workbooks,
)

OWNER = "agent_verify_owner@test.com"
OUTSIDER = "agent_verify_outsider@test.com"
WORKBOOK_TITLE = "Agent Verify Workbook"
TODO_PREFIX = "Agent Verify"
TODOS = [f"{TODO_PREFIX} one", f"{TODO_PREFIX} two"]


def todo_operations():
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
        },
        {
            "type": "filter",
            "column": {"type": "column", "column_name": "description"},
            "operator": "contains",
            "value": TODO_PREFIX,
        },
    ]


def table_config(row_column="description"):
    return {
        "limit": 50,
        "rows": [{"column_name": row_column, "data_type": "String"}],
        "columns": [],
        "values": [{"measure_name": "Tasks", "column_name": "count", "aggregation": "count"}],
        "order_by": [],
    }


def layout(i):
    return {"i": i, "x": 0, "y": 0, "w": 4, "h": 4}


def filter_item(name, links, i="filter-1"):
    return {
        "type": "filter",
        "filter_name": name,
        "filter_type": "String",
        "links": links,
        "layout": layout(i),
    }


class TestVerifyWorkbook(InsightsIntegrationTestCase):
    SAVEPOINT = "test_agent_verify"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cls.cleanup()
        create_user(OWNER, roles="Insights User")
        create_user(OUTSIDER, roles="Insights User")
        for description in TODOS:
            # ToDo reads only what is allocated to the reader
            frappe.get_doc({"doctype": "ToDo", "description": description, "allocated_to": OWNER}).insert(
                ignore_permissions=True
            )

    @classmethod
    def after_class(cls):
        cls.cleanup()
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.original_enable_permissions)

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for todo in frappe.get_all(
            "ToDo", filters={"description": ["like", f"{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        delete_users(OWNER, OUTSIDER)

    def make_workbook(self, config=None):
        """A workbook whose one chart counts the fixture tasks, on a dashboard
        with a Description filter linked to the chart's query."""
        workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name
        query = create_test_query(OWNER, workbook, title="Tasks", operations=todo_operations()).name
        chart = create_test_chart(
            OWNER, workbook, query=query, title="Tasks", chart_type="Table", config=config or table_config()
        ).name
        dashboard = create_test_dashboard(
            OWNER,
            workbook,
            title="Tasks",
            items=[
                {"type": "chart", "chart": chart, "layout": layout("chart-1")},
                filter_item("Description", {chart: f"`{query}`.`description`"}),
            ],
        ).name
        return workbook, query, chart, dashboard

    def set_items(self, dashboard, items):
        frappe.db.set_value(DT.DASHBOARD, dashboard, "items", frappe.as_json(items))

    def verify(self, workbook, user=OWNER, **kwargs):
        with as_user(user), db_connections():
            return verify_workbook(workbook=workbook, **kwargs)

    # @feature tooling.agent-verify-workbook
    def test_a_workbook_that_renders_verifies_with_each_run_reported(self):
        workbook, query, chart, _ = self.make_workbook()

        result = self.verify(workbook, filters={"Description": {"operator": "=", "value": TODOS[0]}})

        self.assertTrue(result["ok"], result)
        [query_entry] = result["queries"]
        self.assertEqual(query_entry["name"], query)
        self.assertEqual(query_entry["rows"], len(TODOS))
        self.assertIn("description", query_entry["columns"])
        self.assertEqual(
            [(c["name"], c["ok"], c["rows"]) for c in result["charts"]],
            [(chart, True, len(TODOS))],
        )
        [dashboard_entry] = result["dashboards"]
        self.assertEqual(dashboard_entry["errors"], [])
        self.assertEqual(
            dashboard_entry["charts"],
            [{"name": chart, "filters": ["Description"], "rows": 1, "ok": True}],
        )

    # @feature tooling.agent-verify-workbook
    def test_a_chart_naming_a_column_its_query_lacks_fails_with_the_run_error(self):
        workbook, *_ = self.make_workbook(config=table_config(row_column="no_such_column"))

        [chart] = self.verify(workbook)["charts"]

        self.assertFalse(chart["ok"])
        self.assertIn("no_such_column", " ".join(chart["errors"]))

    # @feature tooling.agent-verify-workbook
    def test_a_sort_the_result_lacks_is_named_and_fails_a_chart_only_with_a_limit(self):
        sort = [{"column": {"column_name": "no_such_column"}, "direction": "desc"}]
        unlimited = {**table_config(), "limit": None, "order_by": sort}
        limited = {**table_config(), "order_by": sort}

        for config, ok in ((unlimited, True), (limited, False)):
            with self.subTest(limit=config["limit"]):
                workbook, *_ = self.make_workbook(config=config)

                [chart] = self.verify(workbook)["charts"]

                self.assertEqual(chart["unresolved_order_by"], ["no_such_column"])
                self.assertEqual(chart["ok"], ok)

    # @feature tooling.agent-verify-workbook
    def test_a_sort_on_a_result_column_is_not_reported(self):
        sort = [{"column": {"column_name": "Tasks"}, "direction": "desc"}]
        workbook, *_ = self.make_workbook(config={**table_config(), "order_by": sort})

        [chart] = self.verify(workbook)["charts"]

        self.assertTrue(chart["ok"], chart)
        self.assertNotIn("unresolved_order_by", chart)

    # @feature tooling.agent-verify-workbook
    def test_a_chart_missing_a_required_slot_reports_what_the_builder_shows(self):
        workbook, *_ = self.make_workbook(config={"rows": [], "values": []})

        [chart] = self.verify(workbook)["charts"]

        self.assertEqual(chart["errors"], ["Rows are required"])
        self.assertFalse(chart["ok"])

    # @feature tooling.agent-verify-workbook
    def test_dashboard_items_that_do_not_resolve_are_each_named(self):
        workbook, query, chart, dashboard = self.make_workbook()
        other = create_test_query(OWNER, workbook, title="Other", operations=todo_operations()).name
        self.set_items(
            dashboard,
            [
                {"type": "chart", "chart": chart, "layout": layout("chart-1")},
                {"type": "chart", "chart": "no-such-chart", "layout": layout("chart-2")},
                filter_item("Other", {chart: f"`{other}`.`description`"}),
                filter_item("Missing", {chart: f"`{query}`.`no_such_column`"}, "filter-2"),
            ],
        )

        result = self.verify(workbook, filters={"Status": {"operator": "=", "value": "Open"}})

        [entry] = result["dashboards"]
        self.assertFalse(result["ok"])
        self.assertEqual(
            entry["errors"],
            [
                "item 1 (chart 'no-such-chart') is not a chart you may read",
                f"item 2 (filter 'Other') links chart {chart!r} to query {other!r}, which that chart does not read",
                f"item 3 (filter 'Missing') links column 'no_such_column', which query {query!r} does not have",
            ],
        )
        self.assertEqual(result["errors"], ["filter 'Status' is on no dashboard of this workbook"])
        self.assertEqual([c["name"] for c in entry["charts"]], [chart])

    # @feature tooling.agent-verify-workbook
    def test_a_chart_of_another_workbook_on_the_dashboard_renders_there(self):
        workbook, query, chart, dashboard = self.make_workbook()
        other_workbook = create_test_workbook(OWNER, title=f"{WORKBOOK_TITLE} 2").name
        other_query = create_test_query(OWNER, other_workbook, operations=todo_operations()).name
        other_chart = create_test_chart(
            OWNER, other_workbook, query=other_query, chart_type="Table", config=table_config()
        ).name
        self.set_items(
            dashboard,
            [
                {"type": "chart", "chart": chart, "layout": layout("chart-1")},
                {"type": "chart", "chart": other_chart, "layout": layout("chart-2")},
                filter_item("Description", {chart: f"`{query}`.`description`"}),
            ],
        )

        result = self.verify(workbook, filters={"Description": {"operator": "=", "value": TODOS[0]}})

        self.assertTrue(result["ok"], result)
        [entry] = result["dashboards"]
        self.assertEqual(
            [(c["name"], c["rows"]) for c in entry["charts"]], [(chart, 1), (other_chart, len(TODOS))]
        )

    # @feature tooling.agent-verify-workbook
    def test_each_dashboard_gets_only_the_filters_it_has(self):
        workbook, query, chart, _ = self.make_workbook()
        create_test_dashboard(
            OWNER,
            workbook,
            title="Tasks Too",
            items=[
                {"type": "chart", "chart": chart, "layout": layout("chart-1")},
                filter_item("Task", {chart: f"`{query}`.`description`"}),
            ],
        )

        result = self.verify(
            workbook,
            filters={
                "Description": {"operator": "=", "value": TODOS[0]},
                "Task": {"operator": "=", "value": TODOS[1]},
            },
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(
            [(entry["errors"], [c["filters"] for c in entry["charts"]]) for entry in result["dashboards"]],
            [([], [["Description"]]), ([], [["Task"]])],
        )

    # @feature tooling.agent-verify-workbook
    def test_a_filter_link_resolves_its_column_as_the_routed_filter_does(self):
        workbook, query, chart, dashboard = self.make_workbook()
        self.set_items(
            dashboard,
            [
                {"type": "chart", "chart": chart, "layout": layout("chart-1")},
                filter_item("Description", {chart: f"`{query}`.`Description`"}),
            ],
        )

        [entry] = self.verify(workbook, filters={"Description": {"operator": "=", "value": TODOS[0]}})[
            "dashboards"
        ]

        self.assertEqual(entry["errors"], [])
        self.assertEqual(entry["charts"][0]["rows"], 1)

    # @feature tooling.agent-verify-workbook
    def test_an_expression_error_reads_as_plain_text_and_leaves_the_message_log(self):
        workbook, query, *_ = self.make_workbook()
        frappe.db.set_value(
            DT.QUERY,
            query,
            "operations",
            frappe.as_json(
                [
                    *todo_operations(),
                    {
                        "type": "mutate",
                        "new_name": "flag",
                        "data_type": "Integer",
                        "expression": {"type": "expression", "expression": "no_such_column > 5"},
                    },
                ]
            ),
        )
        frappe.local.message_log = []

        [entry] = self.verify(workbook)["queries"]

        self.assertIn("no_such_column > 5", entry["error"])
        self.assertNotIn("&gt;", entry["error"])
        self.assertEqual(frappe.local.message_log, [])

    # @feature tooling.agent-verify-workbook
    def test_a_query_reading_a_failing_query_names_both_operations_once(self):
        workbook, query, *_ = self.make_workbook()
        bad_mutate = {
            "type": "mutate",
            "new_name": "flag",
            "data_type": "Integer",
            "expression": {"type": "expression", "expression": "no_such_column > 5"},
        }
        frappe.db.set_value(DT.QUERY, query, "operations", frappe.as_json([*todo_operations(), bad_mutate]))
        create_test_query(
            OWNER,
            workbook,
            title="Reads Tasks",
            operations=[{"type": "source", "table": {"type": "query", "query_name": query}}],
        )
        sentinel = {"message": "before the run"}
        frappe.local.message_log = [sentinel]

        reader = next(q for q in self.verify(workbook)["queries"] if q["title"] == "Reads Tasks")

        self.assertTrue(
            reader["error"].startswith(
                "Operation 1 (source): Operation 3 (mutate 'flag') in query 'Tasks': UnknownColumn: "
            ),
            reader["error"],
        )
        self.assertEqual(reader["error"].count("Operation 3"), 1)
        self.assertEqual(frappe.local.message_log, [sentinel])

    # @feature tooling.agent-verify-workbook
    def test_an_error_reports_the_operation_it_failed_in_over_its_own_text(self):
        error = KeyError("flag")
        error.operation_message = "Operation 2 (mutate 'flag'): KeyError: 'flag'"

        self.assertEqual(error_message(error), "Operation 2 (mutate 'flag'): KeyError: 'flag'")

    # @feature tooling.agent-verify-workbook
    def test_a_data_store_query_whose_table_is_not_stored_fails_with_its_charts(self):
        workbook, query, *_ = self.make_workbook()
        frappe.db.set_value(DT.QUERY, query, "use_live_connection", 0)
        WarehouseTable("Site DB", "tabToDo").drop()

        # patched so that a failing run starts no real import
        with patch.object(WarehouseTable, "enqueue_import", return_value=False) as enqueue_import:
            result = self.verify(workbook, filters={"Description": {"operator": "=", "value": TODOS[0]}})
        enqueue_import.assert_not_called()

        [entry] = result["queries"]
        self.assertIn("tabToDo of Site DB is not stored", entry["error"])
        self.assertFalse(entry["ok"])
        [chart] = result["charts"]
        [rendered] = result["dashboards"][0]["charts"]
        for chart_entry in (chart, rendered):
            self.assertEqual(chart_entry["errors"], [entry["error"]])
            self.assertFalse(chart_entry["ok"])
        self.assertFalse(result["ok"])

    # @feature permissions.agent-verify-respects-access
    def test_a_filter_link_to_a_query_the_caller_may_not_read_is_not_run(self):
        workbook, query, chart, dashboard = self.make_workbook()
        outsider_workbook = create_test_workbook(OUTSIDER, title=f"{WORKBOOK_TITLE} Outsider").name
        hidden = create_test_query(OUTSIDER, outsider_workbook, operations=todo_operations()).name
        frappe.db.set_value(
            DT.QUERY,
            query,
            "operations",
            frappe.as_json([{"type": "source", "table": {"type": "query", "query_name": hidden}}]),
        )
        self.set_items(
            dashboard,
            [
                {"type": "chart", "chart": chart, "layout": layout("chart-1")},
                filter_item("Description", {chart: f"`{hidden}`.`description`"}),
            ],
        )

        with patch.object(
            InsightsQueryv3, "execute", autospec=True, side_effect=InsightsQueryv3.execute
        ) as run:
            [entry] = self.verify(workbook)["dashboards"]

        self.assertEqual(
            entry["errors"], [f"item 1 (filter 'Description') links query {hidden!r}, which did not run"]
        )
        self.assertNotIn(hidden, [call.args[0].name for call in run.call_args_list])

    # @feature permissions.agent-verify-respects-access
    def test_a_caller_who_may_not_read_the_workbook_is_answered_not_found(self):
        workbook, *_ = self.make_workbook()

        with self.assertRaises(frappe.DoesNotExistError):
            self.verify(workbook, user=OUTSIDER)
        with self.assertRaises(frappe.DoesNotExistError):
            self.verify("no-such-workbook", user=OUTSIDER)
