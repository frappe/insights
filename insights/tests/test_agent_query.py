"""What an agent reads when it runs a query or profiles its column, saved or not.

Both are query document methods, so they run through `insights.api.run_doc_method`
like the Builder's own calls: on the stored query, or on a pipeline sent under a
`new-` name. Either way they read what the query would read, and are refused what
the query would be refused.
"""

from unittest.mock import patch

import frappe
from frappe.utils import set_request

from insights.api import run_doc_method
from insights.exceptions import TableNotStored, UnknownColumn
from insights.insights.doctype.insights_data_source_v3.data_warehouse import WarehouseTable
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    InsightsDataSourcev3,
    db_connections,
)
from insights.insights.doctype.insights_query_v3 import insights_query_v3
from insights.not_permitted import NotPermitted
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_query, create_test_workbook
from insights.tests.permissions_utils import (
    NON_INSIGHTS_USER,
    USER_1,
    USER_2,
    cleanup_test_fixtures,
    create_test_users,
)

OWNER = USER_1
OUTSIDER = USER_2

TODO_PREFIX = "Agent Query Test"
TODOS = [
    {
        "description": f"{TODO_PREFIX} a",
        "priority": "High",
        "reference_type": "User",
        "reference_name": "Administrator",
    },
    {"description": f"{TODO_PREFIX} b", "priority": "High"},
    {
        "description": f"{TODO_PREFIX} c",
        "priority": "Low",
        "reference_type": "User",
        "reference_name": "Guest",
    },
]


def table_operations(table_name="tabToDo"):
    return [
        {"type": "source", "table": {"type": "table", "data_source": "Site DB", "table_name": table_name}}
    ]


def todo_operations():
    return [
        *table_operations(),
        {
            "type": "filter",
            "column": {"type": "column", "column_name": "description"},
            "operator": "contains",
            "value": TODO_PREFIX,
        },
    ]


def reference_operations(query_name):
    return [{"type": "source", "table": {"type": "query", "query_name": query_name}}]


class TestAgentQuery(InsightsIntegrationTestCase):
    SAVEPOINT = "test_agent_query"

    @classmethod
    def before_class(cls):
        cleanup_test_fixtures()
        cls.delete_todos()
        create_test_users()
        for todo in TODOS:
            frappe.get_doc(
                {"doctype": "ToDo", "allocated_to": OWNER, "assigned_by": "Administrator", **todo}
            ).insert(ignore_permissions=True)

        cls.workbook = create_test_workbook(OWNER, title="Agent Query Workbook").name
        cls.outsider_workbook = create_test_workbook(OUTSIDER, title="Agent Query Outsider Workbook").name
        cls.query = create_test_query(OWNER, cls.workbook, operations=todo_operations()).name

    @classmethod
    def after_class(cls):
        cls.delete_todos()
        cleanup_test_fixtures()

    @classmethod
    def delete_todos(cls):
        for name in frappe.get_all(
            "ToDo", filters={"description": ["like", f"{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)

    def before_test(self):
        self.set_team_permissions(0)
        set_request(method="GET", path="/api/method/insights.api.run_doc_method")

    def call_as(self, user, method, operations=None, query=None, use_live_connection=1, **args):
        """What an agent gets through `run_doc_method`: on the stored `query`, or
        on `operations` sent as a query that is not saved."""
        with self.as_user(user), db_connections():
            if query:
                docs = frappe.get_doc(DT.QUERY, query).as_dict()
            else:
                docs = self.unsaved_query(user, operations, use_live_connection)
            return run_doc_method(method, docs, args)

    def unsaved_query(self, user, operations, use_live_connection=1):
        return {
            "doctype": DT.QUERY,
            "name": "new-query-agent",
            "__islocal": 1,
            "workbook": self.outsider_workbook if user == OUTSIDER else self.workbook,
            "is_builder_query": 1,
            "use_live_connection": use_live_connection,
            "operations": operations,
        }

    def profile_as(self, user, column_name, **kwargs):
        return self.call_as(user, "profile_column", column_name=column_name, **kwargs)

    # @feature tooling.agent-run-unsaved-query
    def test_an_unsaved_pipeline_runs_a_page_without_saving_a_query(self):
        queries = frappe.db.count(DT.QUERY)
        result = self.call_as(OWNER, "execute", operations=todo_operations(), page_size=2)

        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(frappe.db.count(DT.QUERY), queries)

    # @feature tooling.agent-profile-column
    def test_a_profile_counts_ranks_and_covers_a_column(self):
        profile = self.profile_as(OWNER, "reference_name", operations=todo_operations(), by="priority")

        self.assertEqual(
            profile,
            {
                "column": "reference_name",
                "row_count": 3,
                "null_count": 1,
                "distinct_count": 2,
                "min": "Administrator",
                "max": "Guest",
                "top_values": [
                    {"value": "Administrator", "count": 1, "share": 1 / 3},
                    {"value": "Guest", "count": 1, "share": 1 / 3},
                ],
                "by": "priority",
                "coverage": [
                    {"value": "High", "row_count": 2, "non_null_count": 1, "share": 0.5},
                    {"value": "Low", "row_count": 1, "non_null_count": 1, "share": 1.0},
                ],
            },
        )

    # @feature tooling.agent-profile-column
    def test_a_saved_query_profiles_like_its_unsaved_operations(self):
        saved = self.profile_as(OWNER, "priority", query=self.query, limit=1)
        unsaved = self.profile_as(OWNER, "priority", operations=todo_operations(), limit=1)

        self.assertEqual(saved, unsaved)
        self.assertEqual(saved["top_values"], [{"value": "High", "count": 2, "share": 2 / 3}])

    # @feature data-store.run-without-import
    def test_a_data_store_run_that_may_not_import_refuses_a_table_not_stored(self):
        WarehouseTable("Site DB", "tabToDo").drop()

        with patch.object(WarehouseTable, "enqueue_import", return_value=False) as enqueue_import:
            with self.assertRaises(TableNotStored) as refused:
                self.call_as(
                    OWNER,
                    "execute",
                    operations=todo_operations(),
                    use_live_connection=0,
                    import_if_not_exists=False,
                )
            enqueue_import.assert_not_called()

            self.call_as(OWNER, "execute", operations=todo_operations(), use_live_connection=0)
            enqueue_import.assert_called_once()

        self.assertIn("tabToDo of Site DB", str(refused.exception))

    # @feature data-store.run-without-import permissions.get-keeps-no-write
    def test_a_profile_under_get_refuses_a_table_not_stored_and_queues_no_import(self):
        WarehouseTable("Site DB", "tabToDo").drop()

        with self.assertRaises(TableNotStored):
            self.profile_as(OWNER, "priority", operations=todo_operations(), use_live_connection=0)
        self.assert_no_get_writes()

    # @feature data-store.run-without-import
    def test_a_source_other_than_the_site_database_is_named_not_stored_without_a_live_read(self):
        WarehouseTable("Site DB", "tabToDo").drop()
        not_site_db = "insights.insights.doctype.insights_table_v3.insights_table_v3.is_site_db"

        with (
            patch(not_site_db, return_value=False),
            patch.object(InsightsDataSourcev3, "get_ibis_table", side_effect=AssertionError("read live")),
            self.assertRaises(TableNotStored),
        ):
            self.call_as(
                "Administrator",
                "execute",
                operations=table_operations(),
                use_live_connection=0,
                import_if_not_exists=False,
            )

    # @feature permissions.agent-profile-respects-access
    def test_a_table_the_reader_may_not_read_is_refused(self):
        with self.assertRaises(NotPermitted):
            self.profile_as(OWNER, "name", operations=table_operations("tabError Log"))

    # @feature permissions.agent-profile-respects-access data-store.run-without-import
    def test_a_table_the_reader_may_not_read_is_refused_before_it_is_named_not_stored(self):
        WarehouseTable("Site DB", "tabError Log").drop()
        for method, args in (
            ("execute", {"import_if_not_exists": False}),
            ("profile_column", {"column_name": "name"}),
        ):
            frappe.local.message_log = []
            with self.subTest(method=method):
                with self.assertRaises(NotPermitted):
                    self.call_as(
                        OWNER,
                        method,
                        operations=table_operations("tabError Log"),
                        use_live_connection=0,
                        **args,
                    )
                self.assertEqual(
                    [message.get("message") for message in frappe.local.message_log],
                    ["Needs read access to <strong>Error Log</strong>"],
                )

    # @feature tooling.agent-profile-column
    def test_a_profile_refuses_a_name_the_query_lacks(self):
        # `reference_type` is the one column ending in `_type`
        for args in ({"column_name": "type"}, {"column_name": "priority", "by": "type"}):
            with self.subTest(**args), self.assertRaises(UnknownColumn):
                self.call_as(OWNER, "profile_column", operations=todo_operations(), **args)

    # @feature tooling.agent-profile-column
    def test_a_forced_profile_reads_past_the_results_cache(self):
        with patch.object(
            insights_query_v3, "execute_ibis_query", wraps=insights_query_v3.execute_ibis_query
        ) as run:
            self.profile_as(OWNER, "priority", operations=todo_operations(), by="priority", force=True)

        self.assertEqual([call.kwargs["force"] for call in run.call_args_list], [True, True, True])

    # @feature tooling.agent-run-unsaved-query
    def test_a_run_sent_as_get_takes_its_arguments_as_json(self):
        with self.as_user(OWNER), db_connections():
            result = run_doc_method(
                "execute",
                frappe.as_json(self.unsaved_query(OWNER, todo_operations())),
                frappe.as_json({"page_size": 2}),
            )

        self.assertEqual(len(result["rows"]), 2)

    # @feature permissions.agent-profile-respects-access
    def test_a_column_held_back_from_the_reader_is_refused(self):
        self.make_status_permlevel()
        with self.assertRaises(NotPermitted):
            self.profile_as(OWNER, "status", operations=todo_operations())

    # @feature permissions.agent-profile-respects-access
    def test_a_query_the_reader_may_not_read_is_refused(self):
        with self.assertRaises(frappe.PermissionError):
            self.profile_as(OUTSIDER, "priority", query=self.query)
        with self.assertRaises(frappe.PermissionError):
            self.profile_as(OUTSIDER, "priority", operations=reference_operations(self.query))

    # @feature permissions.agent-profile-respects-access
    def test_a_user_without_an_insights_role_is_refused(self):
        with self.assertRaises(frappe.PermissionError):
            self.profile_as(NON_INSIGHTS_USER, "priority", operations=todo_operations())
