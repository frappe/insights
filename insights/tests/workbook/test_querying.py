from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from insights.insights.doctype.insights_data_source_v3.ibis_utils import CircularQueryReferenceError
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    USER_1,
    as_user,
    cleanup_workbook_flow_fixtures,
    create_test_query,
    create_test_user,
    create_test_workbook,
    execute_test_query,
)

TODO_PREFIX = "Insights Querying Test"


def column(column_name):
    return {"type": "column", "column_name": column_name}


def table_source(table_name="tabToDo"):
    return {
        "type": "source",
        "table": {
            "type": "table",
            "data_source": "Site DB",
            "table_name": table_name,
        },
    }


def query_source(query_name):
    return {
        "type": "source",
        "table": {
            "type": "query",
            "query_name": query_name,
        },
    }


class TestQuerying(InsightsIntegrationTestCase):
    COMMIT_AFTER_TEST_SETUP = True
    COMMIT_AFTER_TEST_TEARDOWN = True

    @classmethod
    def before_class(cls):
        cleanup_workbook_flow_fixtures()
        cls.delete_test_todos()
        create_test_user(USER_1)

    @classmethod
    def after_class(cls):
        cls.delete_test_todos()
        cleanup_workbook_flow_fixtures()

    def before_test(self):
        self.delete_test_todos()
        cleanup_workbook_flow_fixtures()
        create_test_user(USER_1)

    def after_test(self):
        self.delete_test_todos()
        cleanup_workbook_flow_fixtures()

    @staticmethod
    def delete_test_todos():
        todo_names = frappe.get_all(
            "ToDo",
            filters={"description": ["like", f"{TODO_PREFIX}%"]},
            pluck="name",
        )
        for todo_name in todo_names:
            frappe.delete_doc("ToDo", todo_name, force=True)

    def seed_todos(self):
        records = [
            {
                "description": f"{TODO_PREFIX} Open Alpha",
                "status": "Open",
                "date": add_days(nowdate(), 1),
                "allocated_to": USER_1,
            },
            {
                "description": f"{TODO_PREFIX} Closed Beta",
                "status": "Closed",
                "date": add_days(nowdate(), 2),
                "allocated_to": USER_1,
            },
            {
                "description": f"{TODO_PREFIX} Open Gamma",
                "status": "Open",
                "date": add_days(nowdate(), 3),
                "allocated_to": USER_1,
            },
        ]

        todo_names = []
        for record in records:
            todo = frappe.get_doc({"doctype": "ToDo", **record}).insert(ignore_permissions=True)
            todo_names.append(todo.name)

        # The query reads tabToDo over the Site DB source's own ibis.mysql connection.
        frappe.db.commit()  # nosemgrep
        return todo_names

    def get_query(self, query_name):
        return frappe.get_doc(DT.QUERY, query_name)

    # @feature query.source-table
    def test_builder_query_executes_from_source_operation(self):
        data_sources = set(frappe.get_all("Insights Data Source v3", pluck="name"))

        self.assertIn("Site DB", data_sources)

        workbook = create_test_workbook(USER_1)
        query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Smoke",
        )

        result = execute_test_query(query.name)

        self.assertIn("sql", result)
        self.assertGreater(len(result["columns"]), 0)
        self.assertIsInstance(result["rows"], list)

    # @feature query.filter query.limit query.mutate query.order-by
    def test_query_pipeline_supports_filter_group_mutate_order_and_limit(self):
        self.seed_todos()
        workbook = create_test_workbook(USER_1)
        query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Pipeline",
            operations=[
                table_source(),
                {
                    "type": "filter_group",
                    "logical_operator": "And",
                    "filters": [
                        {
                            "column": column("description"),
                            "operator": "contains",
                            "value": TODO_PREFIX,
                        },
                        {
                            "column": column("status"),
                            "operator": "=",
                            "value": "Open",
                        },
                    ],
                },
                {
                    "type": "mutate",
                    "new_name": "docstatus_plus_one",
                    "expression": {"type": "expression", "expression": "docstatus + 1"},
                    "data_type": "Integer",
                },
                {
                    "type": "order_by",
                    "column": column("description"),
                    "direction": "asc",
                },
                {"type": "limit", "limit": 2},
            ],
        )

        with db_connections():
            preview_columns = self.get_query(query.name).get_columns_for_selection(active_operation_idx=2)

        result = execute_test_query(query.name)
        preview_column_names = {col["name"] for col in preview_columns}

        self.assertIn("docstatus_plus_one", preview_column_names)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(
            [row["description"] for row in result["rows"]],
            [
                f"{TODO_PREFIX} Open Alpha",
                f"{TODO_PREFIX} Open Gamma",
            ],
        )
        self.assertTrue(all(row["docstatus_plus_one"] == 1 for row in result["rows"]))

    # @feature query.filter query.join
    def test_query_pipeline_supports_filter_and_join(self):
        self.seed_todos()
        workbook = create_test_workbook(USER_1)
        query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Join",
            operations=[
                table_source(),
                {
                    "type": "filter",
                    "column": column("description"),
                    "operator": "contains",
                    "value": TODO_PREFIX,
                },
                {
                    "type": "join",
                    "join_type": "left",
                    "table": {
                        "type": "table",
                        "data_source": "Site DB",
                        "table_name": "tabUser",
                    },
                    "select_columns": [column("full_name")],
                    "join_condition": {
                        "left_column": column("allocated_to"),
                        "right_column": column("name"),
                    },
                },
                {
                    "type": "order_by",
                    "column": column("description"),
                    "direction": "asc",
                },
            ],
        )

        with db_connections():
            preview_columns = self.get_query(query.name).get_columns_for_selection(active_operation_idx=2)

        result = execute_test_query(query.name)
        preview_column_names = {col["name"] for col in preview_columns}

        self.assertIn("full_name", preview_column_names)
        self.assertEqual(len(result["rows"]), 3)
        self.assertEqual({row["full_name"] for row in result["rows"]}, {"Workbook Flow User"})

    # @feature query.summarize
    def test_query_summary_groups_filtered_rows_by_status(self):
        self.seed_todos()
        workbook = create_test_workbook(USER_1)
        query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Summary",
            operations=[
                table_source(),
                {
                    "type": "filter",
                    "column": column("description"),
                    "operator": "contains",
                    "value": TODO_PREFIX,
                },
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "measure_name": "todo_count",
                            "column_name": "name",
                            "aggregation": "count",
                        }
                    ],
                    "dimensions": [
                        {
                            "column_name": "status",
                            "data_type": "String",
                            "dimension_name": "status",
                        }
                    ],
                },
                {
                    "type": "order_by",
                    "column": column("status"),
                    "direction": "asc",
                },
            ],
        )

        result = execute_test_query(query.name)
        summary = {row["status"]: row["todo_count"] for row in result["rows"]}

        self.assertEqual(summary, {"Closed": 1, "Open": 2})

    # @feature query.download-results query.filter-values query.row-count
    def test_query_helpers_return_count_distinct_values_and_csv_results(self):
        self.seed_todos()
        workbook = create_test_workbook(USER_1)
        query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Helpers",
            operations=[
                table_source(),
                {
                    "type": "filter",
                    "column": column("description"),
                    "operator": "contains",
                    "value": TODO_PREFIX,
                },
            ],
        )
        query_doc = self.get_query(query.name)

        with db_connections():
            total_count = query_doc.get_count()
            distinct_statuses = query_doc.get_distinct_column_values("status")
            csv_data = query_doc.download_results(format="csv")

        self.assertEqual(total_count, 3)
        self.assertEqual(set(distinct_statuses), {"Closed", "Open"})
        self.assertIn("description", csv_data)
        self.assertIn(f"{TODO_PREFIX} Open Alpha", csv_data)
        self.assertIn(f"{TODO_PREFIX} Closed Beta", csv_data)

    # @feature query.filter-values
    def test_distinct_values_of_an_all_null_column_stay_empty_when_cached(self):
        self.seed_todos()
        workbook = create_test_workbook(USER_1)
        query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Null Column",
            operations=[
                table_source(),
                {
                    "type": "filter",
                    "column": column("description"),
                    "operator": "contains",
                    "value": TODO_PREFIX,
                },
            ],
        )
        query_doc = self.get_query(query.name)

        with db_connections():
            # no seeded todo sets a color, so the first call caches an empty result
            first = query_doc.get_distinct_column_values("color")
            second = query_doc.get_distinct_column_values("color")

        self.assertEqual(first, [])
        self.assertEqual(second, [])

    # @feature query.source-query
    def test_query_can_use_another_query_as_its_source(self):
        self.seed_todos()
        workbook = create_test_workbook(USER_1)
        base_query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Base",
            operations=[
                table_source(),
                {
                    "type": "filter",
                    "column": column("description"),
                    "operator": "contains",
                    "value": TODO_PREFIX,
                },
            ],
        )
        derived_query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Derived",
            operations=[
                query_source(base_query.name),
                {
                    "type": "summarize",
                    "measures": [
                        {
                            "measure_name": "todo_count",
                            "column_name": "name",
                            "aggregation": "count",
                        }
                    ],
                    "dimensions": [
                        {
                            "column_name": "status",
                            "data_type": "String",
                            "dimension_name": "status",
                        }
                    ],
                },
            ],
        )

        result = execute_test_query(derived_query.name)

        with db_connections():
            source_tables = self.get_query(derived_query.name).get_source_tables()

        self.assertEqual(
            {row["status"]: row["todo_count"] for row in result["rows"]}, {"Closed": 1, "Open": 2}
        )
        self.assertEqual(source_tables, [{"data_source": "Site DB", "table_name": "tabToDo"}])

    # @feature query.source-cycle-refused
    def test_query_validation_blocks_circular_query_references(self):
        workbook = create_test_workbook(USER_1)
        first_query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Circular First",
            operations=[table_source()],
        )
        second_query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Circular Second",
            operations=[query_source(first_query.name)],
        )

        first_query_doc = self.get_query(first_query.name)
        first_query_doc.operations = [query_source(second_query.name)]

        with self.assertRaises(CircularQueryReferenceError):
            first_query_doc.save()

    def seed_todo_without_a_date(self):
        todo = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": f"{TODO_PREFIX} Undated Delta",
                "status": "Open",
                "allocated_to": USER_1,
            }
        ).insert(ignore_permissions=True)
        frappe.db.set_value("ToDo", todo.name, "date", None, update_modified=False)
        # The emptied date has to be on disk for the source's own connection to read it.
        frappe.db.commit()  # nosemgrep
        return todo.name

    def seed_unassigned_todo(self):
        todo = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": f"{TODO_PREFIX} Orphan Delta",
                "status": "Open",
                "date": add_days(nowdate(), 4),
            }
        ).insert(ignore_permissions=True)
        # The query reads tabToDo over the Site DB source's own ibis.mysql connection.
        frappe.db.commit()  # nosemgrep
        return todo.name

    def prefix_filter(self):
        return {
            "type": "filter",
            "column": column("description"),
            "operator": "contains",
            "value": TODO_PREFIX,
        }

    def run_pipeline(self, title, operations):
        workbook = create_test_workbook(USER_1)
        query = create_test_query(USER_1, workbook.name, title=title, operations=operations)
        return execute_test_query(query.name)

    # @feature query.select-columns query.select-columns-order
    def test_a_select_keeps_only_the_chosen_columns_in_the_order_they_were_chosen(self):
        self.seed_todos()

        result = self.run_pipeline(
            "Workbook Flow Test Query Select",
            [
                table_source(),
                self.prefix_filter(),
                {"type": "select", "column_names": ["status", "description"]},
                {"type": "order_by", "column": column("description"), "direction": "asc"},
            ],
        )

        self.assertEqual([col["name"] for col in result["columns"]], ["status", "description"])
        self.assertEqual(
            result["rows"],
            [
                {"status": "Closed", "description": f"{TODO_PREFIX} Closed Beta"},
                {"status": "Open", "description": f"{TODO_PREFIX} Open Alpha"},
                {"status": "Open", "description": f"{TODO_PREFIX} Open Gamma"},
            ],
        )

        flipped = self.run_pipeline(
            "Workbook Flow Test Query Select Flipped",
            [
                table_source(),
                self.prefix_filter(),
                {"type": "select", "column_names": ["description", "status"]},
                {"type": "order_by", "column": column("description"), "direction": "asc"},
            ],
        )

        self.assertEqual([col["name"] for col in flipped["columns"]], ["description", "status"])

    # @feature query.filter-and-or
    def test_an_or_group_keeps_a_row_matching_either_rule_and_an_and_group_needs_both(self):
        self.seed_todos()

        def run(logical_operator):
            return self.run_pipeline(
                f"Workbook Flow Test Query Filter {logical_operator}",
                [
                    table_source(),
                    self.prefix_filter(),
                    {
                        "type": "filter_group",
                        "logical_operator": logical_operator,
                        "filters": [
                            {"column": column("status"), "operator": "=", "value": "Closed"},
                            {
                                "column": column("description"),
                                "operator": "contains",
                                "value": "Gamma",
                            },
                        ],
                    },
                    {"type": "order_by", "column": column("description"), "direction": "asc"},
                ],
            )

        either = run("Or")
        both = run("And")

        self.assertEqual(
            [row["description"] for row in either["rows"]],
            [f"{TODO_PREFIX} Closed Beta", f"{TODO_PREFIX} Open Gamma"],
        )
        self.assertEqual(both["rows"], [])

    # @feature query.filter-is-set
    def test_is_set_keeps_the_rows_holding_a_value_and_is_not_set_keeps_the_rest(self):
        self.seed_todos()
        self.seed_todo_without_a_date()

        def run(operator):
            return self.run_pipeline(
                f"Workbook Flow Test Query {operator}",
                [
                    table_source(),
                    self.prefix_filter(),
                    {"type": "filter", "column": column("date"), "operator": operator, "value": None},
                    {"type": "order_by", "column": column("description"), "direction": "asc"},
                ],
            )

        dated = run("is_set")
        undated = run("is_not_set")

        self.assertEqual(
            [row["description"] for row in dated["rows"]],
            [
                f"{TODO_PREFIX} Closed Beta",
                f"{TODO_PREFIX} Open Alpha",
                f"{TODO_PREFIX} Open Gamma",
            ],
        )
        self.assertEqual(
            [row["description"] for row in undated["rows"]],
            [f"{TODO_PREFIX} Undated Delta"],
        )

    # @feature query.filter-expression
    def test_a_filter_written_as_an_expression_narrows_like_a_rule(self):
        self.seed_todos()

        result = self.run_pipeline(
            "Workbook Flow Test Query Filter Expression",
            [
                table_source(),
                self.prefix_filter(),
                {
                    "type": "filter",
                    "expression": {"type": "expression", "expression": "status == 'Open'"},
                },
                {"type": "order_by", "column": column("description"), "direction": "asc"},
            ],
        )

        self.assertEqual(
            [row["description"] for row in result["rows"]],
            [f"{TODO_PREFIX} Open Alpha", f"{TODO_PREFIX} Open Gamma"],
        )

    # @feature query.join-type
    def test_a_left_join_keeps_a_row_the_right_table_does_not_match_and_an_inner_join_drops_it(self):
        self.seed_todos()
        self.seed_unassigned_todo()

        def run(join_type):
            return self.run_pipeline(
                f"Workbook Flow Test Query Join {join_type}",
                [
                    table_source(),
                    self.prefix_filter(),
                    {
                        "type": "join",
                        "join_type": join_type,
                        "table": {
                            "type": "table",
                            "data_source": "Site DB",
                            "table_name": "tabUser",
                        },
                        "select_columns": [column("full_name")],
                        "join_condition": {
                            "left_column": column("allocated_to"),
                            "right_column": column("name"),
                        },
                    },
                    {"type": "select", "column_names": ["description", "full_name"]},
                    {"type": "order_by", "column": column("description"), "direction": "asc"},
                ],
            )

        left = run("left")
        inner = run("inner")

        self.assertEqual(
            [(row["description"], row["full_name"]) for row in left["rows"]],
            [
                (f"{TODO_PREFIX} Closed Beta", "Workbook Flow User"),
                (f"{TODO_PREFIX} Open Alpha", "Workbook Flow User"),
                (f"{TODO_PREFIX} Open Gamma", "Workbook Flow User"),
                (f"{TODO_PREFIX} Orphan Delta", None),
            ],
        )
        self.assertEqual(
            [(row["description"], row["full_name"]) for row in inner["rows"]],
            [
                (f"{TODO_PREFIX} Closed Beta", "Workbook Flow User"),
                (f"{TODO_PREFIX} Open Alpha", "Workbook Flow User"),
                (f"{TODO_PREFIX} Open Gamma", "Workbook Flow User"),
            ],
        )

    # @feature query.join-columns-to-add
    def test_a_join_takes_only_the_columns_the_author_picked_from_the_right_table(self):
        self.seed_todos()

        result = self.run_pipeline(
            "Workbook Flow Test Query Join Columns",
            [
                table_source(),
                self.prefix_filter(),
                {
                    "type": "join",
                    "join_type": "left",
                    "table": {
                        "type": "table",
                        "data_source": "Site DB",
                        "table_name": "tabUser",
                    },
                    "select_columns": [column("full_name")],
                    "join_condition": {
                        "left_column": column("allocated_to"),
                        "right_column": column("name"),
                    },
                },
            ],
        )

        result_columns = [col["name"] for col in result["columns"]]

        self.assertIn("full_name", result_columns)
        self.assertNotIn("email", result_columns)

    # @feature query.join-expression
    def test_a_join_written_as_an_expression_matches_on_it(self):
        self.seed_todos()

        result = self.run_pipeline(
            "Workbook Flow Test Query Join Expression",
            [
                table_source(),
                self.prefix_filter(),
                {
                    "type": "join",
                    "join_type": "inner",
                    "table": {
                        "type": "table",
                        "data_source": "Site DB",
                        "table_name": "tabUser",
                    },
                    "select_columns": [column("full_name")],
                    "join_condition": {
                        "join_expression": {
                            "type": "expression",
                            "expression": "t1.allocated_to == t2.name",
                        }
                    },
                },
                {"type": "order_by", "column": column("description"), "direction": "asc"},
            ],
        )

        self.assertEqual(
            [(row["description"], row["full_name"]) for row in result["rows"]],
            [
                (f"{TODO_PREFIX} Closed Beta", "Workbook Flow User"),
                (f"{TODO_PREFIX} Open Alpha", "Workbook Flow User"),
                (f"{TODO_PREFIX} Open Gamma", "Workbook Flow User"),
            ],
        )

    # @feature query.union-distinct
    def test_a_union_with_distinct_drops_the_rows_that_appear_twice(self):
        self.seed_todos()
        workbook = create_test_workbook(USER_1)
        other_query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Union Other",
            operations=[table_source(), self.prefix_filter()],
        )

        def run(distinct):
            query = create_test_query(
                USER_1,
                workbook.name,
                title=f"Workbook Flow Test Query Union {distinct}",
                operations=[
                    table_source(),
                    self.prefix_filter(),
                    {
                        "type": "union",
                        "table": {"type": "query", "query_name": other_query.name},
                        "distinct": distinct,
                    },
                ],
            )
            return execute_test_query(query.name)

        kept_twice = run(False)
        deduplicated = run(True)

        self.assertEqual(len(kept_twice["rows"]), 6)
        self.assertEqual(len(deduplicated["rows"]), 3)
        self.assertEqual(
            sorted(row["description"] for row in deduplicated["rows"]),
            [
                f"{TODO_PREFIX} Closed Beta",
                f"{TODO_PREFIX} Open Alpha",
                f"{TODO_PREFIX} Open Gamma",
            ],
        )

    # @feature query.summarize-aggregations
    def test_each_aggregation_reads_the_seeded_todos_as_its_own_number(self):
        todo_names = self.seed_todos()
        for position, todo_name in enumerate(sorted(todo_names), start=1):
            frappe.db.set_value("ToDo", todo_name, "idx", position, update_modified=False)
        # idx is read back over the Site DB source's own ibis.mysql connection.
        frappe.db.commit()  # nosemgrep

        result = self.run_pipeline(
            "Workbook Flow Test Query Aggregations",
            [
                table_source(),
                self.prefix_filter(),
                {
                    "type": "summarize",
                    "measures": [
                        {"measure_name": "todos", "column_name": "name", "aggregation": "count"},
                        {
                            "measure_name": "statuses",
                            "column_name": "status",
                            "aggregation": "count_distinct",
                        },
                        {"measure_name": "first_date", "column_name": "date", "aggregation": "min"},
                        {"measure_name": "last_date", "column_name": "date", "aggregation": "max"},
                        {"measure_name": "idx_total", "column_name": "idx", "aggregation": "sum"},
                        {"measure_name": "idx_mean", "column_name": "idx", "aggregation": "avg"},
                    ],
                    "dimensions": [],
                },
            ],
        )

        self.assertEqual(len(result["rows"]), 1)
        row = result["rows"][0]

        self.assertEqual(row["todos"], 3)
        self.assertEqual(row["statuses"], 2)
        self.assertEqual(str(row["first_date"])[:10], add_days(nowdate(), 1))
        self.assertEqual(str(row["last_date"])[:10], add_days(nowdate(), 3))
        self.assertEqual(row["idx_total"], 6)
        self.assertEqual(row["idx_mean"], 2)

    # @feature query.custom-operation
    def test_a_custom_operation_runs_its_expression_over_the_table(self):
        self.seed_todos()

        result = self.run_pipeline(
            "Workbook Flow Test Query Custom Operation",
            [
                table_source(),
                self.prefix_filter(),
                {
                    "type": "custom_operation",
                    "expression": {
                        "type": "expression",
                        "expression": "q.filter(q.status == 'Open')",
                    },
                },
                {"type": "order_by", "column": column("description"), "direction": "asc"},
            ],
        )

        self.assertEqual(
            [row["description"] for row in result["rows"]],
            [f"{TODO_PREFIX} Open Alpha", f"{TODO_PREFIX} Open Gamma"],
        )

    def site_db_todo_table(self):
        """The `Insights Table v3` row a refresh looks the source table up by."""
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

        name = get_table_name("Site DB", "tabToDo")
        if not frappe.db.exists(DT.TABLE, name):
            frappe.get_doc(
                {
                    "doctype": DT.TABLE,
                    "table": "tabToDo",
                    "label": "tabToDo",
                    "data_source": "Site DB",
                    "sync_mode": "Full",
                }
            ).insert(ignore_permissions=True)
            self.addCleanup(frappe.delete_doc, DT.TABLE, name, force=True, ignore_permissions=True)
        return name

    # @feature query.refresh-stored-tables
    def test_refreshing_stored_tables_imports_every_source_table_the_query_reads_and_refuses_a_reader(
        self,
    ):
        self.site_db_todo_table()
        workbook = create_test_workbook(USER_1)
        query = create_test_query(
            USER_1,
            workbook.name,
            title="Workbook Flow Test Query Refresh",
            operations=[table_source(), self.prefix_filter()],
        )

        # a stale "In Progress" log left on the site would make the importer
        # report an import already under way and queue nothing
        frappe.db.delete(
            "Insights Table Import Log",
            {"data_source": "Site DB", "table_name": "tabToDo", "status": "In Progress"},
        )

        # the queue is the boundary: the import itself is a background job, and
        # whether one is already sitting on the queue is the queue's state, not
        # this rule's
        warehouse = "insights.insights.doctype.insights_data_source_v3.data_warehouse"
        with (
            patch(f"{warehouse}.is_job_enqueued", return_value=False),
            patch(f"{warehouse}.enqueue_warehouse_table_import") as enqueue,
        ):
            answer = self.get_query(query.name).refresh_stored_tables()

        self.assertEqual(answer["count"], 1)
        self.assertIn("1 table(s)", answer["message"])
        enqueue.assert_called_once_with(data_source="Site DB", table_name="tabToDo")

        # a query that names no table has nothing to import. It is built here
        # rather than through the factory, whose empty-operations fallback is the
        # default source.
        with as_user(USER_1):
            sourceless = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Workbook Flow Test Query Refresh Sourceless",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": [],
                }
            ).insert()

        with self.assertRaises(frappe.ValidationError) as refusal:
            self.get_query(sourceless.name).refresh_stored_tables()

        self.assertIn("No tables found", str(refusal.exception))

        # and a reader may not import at all
        with as_user(USER_1), self.assertRaises(frappe.PermissionError):
            self.get_query(query.name).refresh_stored_tables()
