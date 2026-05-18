import frappe
from frappe.utils import add_days, nowdate

from insights.insights.doctype.insights_data_source_v3.ibis_utils import CircularQueryReferenceError
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    USER_1,
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

        frappe.db.commit()
        return todo_names

    def get_query(self, query_name):
        return frappe.get_doc(DT.QUERY, query_name)

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

        frappe.db.commit()
        result = execute_test_query(derived_query.name)

        with db_connections():
            source_tables = self.get_query(derived_query.name).get_source_tables()

        self.assertEqual(
            {row["status"]: row["todo_count"] for row in result["rows"]}, {"Closed": 1, "Open": 2}
        )
        self.assertEqual(source_tables, [{"data_source": "Site DB", "table_name": "tabToDo"}])

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

        frappe.db.commit()
        first_query_doc = self.get_query(first_query.name)
        first_query_doc.operations = [query_source(second_query.name)]

        with self.assertRaises(CircularQueryReferenceError):
            first_query_doc.save()
