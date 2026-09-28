"""What a failed run reports, and what it keeps.

A failure is worth counting by kind, by interface and by connection. The kinds
are a closed list, so one series answers what breaks most. The reason itself —
the SQL, the driver's words, the names of columns and tables — never leaves the
site.
"""

from unittest.mock import patch

import frappe
from ibis.common.exceptions import OperationNotDefinedError
from pymysql.err import OperationalError

from insights.exceptions import (
    ExpressionSyntaxError,
    QueryRefused,
    QueryTimeout,
    UnknownColumn,
)
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    CircularQueryReferenceError,
    IbisQueryBuilder,
)
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    DataSourceConnectionError,
    db_connections,
)
from insights.telemetry import error_kind
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_query,
    create_test_workbook,
    delete_workbooks,
)

WORKBOOK_TITLE = "Query Failed Test Workbook"
FIRST_TITLE = f"{WORKBOOK_TITLE} Cycle First"
SECOND_TITLE = f"{WORKBOOK_TITLE} Cycle Second"

TODO_SOURCE = {
    "type": "source",
    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
}


def query_source(query_name):
    return {"type": "source", "table": {"type": "query", "query_name": query_name}}


def query_union(query_name):
    return {
        "type": "union",
        "table": {"type": "query", "query_name": query_name},
        "distinct": True,
    }


class TestErrorKind(InsightsIntegrationTestCase):
    # @feature telemetry.query-failed
    def test_an_expression_the_engine_cannot_read_is_a_syntax_error(self):
        self.assertEqual(error_kind(ExpressionSyntaxError("Invalid expression: ")), "syntax")
        self.assertEqual(error_kind(ExpressionSyntaxError("Empty code")), "syntax")
        self.assertEqual(error_kind(SyntaxError("unexpected indent")), "syntax")

    # @feature telemetry.query-failed
    def test_a_column_the_table_does_not_have_is_an_unknown_column(self):
        unknown = UnknownColumn("Column status does not exist in the table")
        self.assertEqual(error_kind(unknown), "unknown_column")
        self.assertEqual(error_kind(UnknownColumn("Table or Query not found")), "unknown_column")

    # @feature telemetry.query-failed
    def test_a_refused_read_is_a_permission_error(self):
        self.assertEqual(error_kind(frappe.PermissionError("no access")), "permission")

    # @feature telemetry.query-failed
    def test_an_unreachable_source_is_a_connection_error(self):
        refused = DataSourceConnectionError("Could not connect to the 'Warehouse' data source.")
        self.assertEqual(error_kind(refused), "connection")

    # @feature telemetry.query-failed
    def test_a_failure_the_driver_raises_is_other_and_not_a_connection_error(self):
        """`OperationalError` is a driver's catch-all, so an unknown column wears it too."""
        self.assertEqual(error_kind(OperationalError(1054, "Unknown column 'x' in 'field list'")), "other")
        self.assertEqual(error_kind(OperationalError(2003, "Can't connect to MySQL server")), "other")

    # @feature telemetry.query-failed
    def test_a_run_past_the_execution_limit_is_a_timeout(self):
        thrown = QueryTimeout("Query execution time exceeded the limit of 300 seconds.")
        self.assertEqual(error_kind(thrown), "timeout")

    # @feature telemetry.query-failed
    def test_a_guard_that_stops_a_run_before_it_starts_is_a_refusal(self):
        self.assertEqual(error_kind(CircularQueryReferenceError("Circular query reference")), "refused")
        self.assertEqual(error_kind(OperationNotDefinedError("ArrayFlatten")), "refused")
        unknown_operation = QueryRefused("This query uses an operation this version does not know: teleport")
        self.assertEqual(error_kind(unknown_operation), "refused")
        self.assertEqual(
            error_kind(QueryRefused("Multiple SQL statements are not supported for native queries")),
            "refused",
        )

    # @feature telemetry.query-failed
    def test_a_filter_operator_the_engine_does_not_know_is_a_refusal(self):
        query = frappe._dict(
            name="Unknown Operator Query",
            title="Unknown Operator Query",
            use_live_connection=1,
            operations=frappe.as_json(
                [
                    TODO_SOURCE,
                    {
                        "type": "filter",
                        "column": {"type": "column", "column_name": "status"},
                        "operator": "teleport",
                        "value": "Open",
                    },
                ]
            ),
        )
        with self.assertRaises(QueryRefused) as refusal, db_connections():
            IbisQueryBuilder(query).build()
        self.assertEqual(error_kind(refusal.exception), "refused")

    # @feature telemetry.query-failed
    def test_a_kind_survives_a_translated_or_reworded_message(self):
        self.assertEqual(error_kind(QueryRefused("Cette requête utilise une opération inconnue")), "refused")
        self.assertEqual(error_kind(UnknownColumn("")), "unknown_column")
        self.assertEqual(error_kind(QueryTimeout("La requête a dépassé la limite")), "timeout")
        self.assertEqual(error_kind(ExpressionSyntaxError("Expression invalide")), "syntax")

    # @feature telemetry.query-failed
    def test_a_failure_nothing_recognises_is_other(self):
        self.assertEqual(error_kind(RuntimeError("the worker went away")), "other")


class TestQueryFailedEvent(InsightsIntegrationTestCase):
    """A run the engine refuses, provoked by a cycle between two queries.

    Save-time validation rejects a cycle, so the second reference is written to
    the row, and the refusal comes from the builder.
    """

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook("Administrator", title=WORKBOOK_TITLE).name
        cls.query = create_test_query(
            "Administrator",
            cls.workbook,
            title=FIRST_TITLE,
            operations=[TODO_SOURCE],
        ).name
        cls.referenced = create_test_query(
            "Administrator",
            cls.workbook,
            title=SECOND_TITLE,
            operations=[query_source(cls.query)],
        ).name
        frappe.db.set_value(
            DT.QUERY,
            cls.query,
            "operations",
            frappe.as_json([TODO_SOURCE, query_union(cls.referenced)]),
        )

    @classmethod
    def after_class(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)

    def refused_run(self):
        """Run the query the engine has to refuse, and return the call it sent."""
        query = frappe.get_doc(DT.QUERY, self.query)
        with patch("frappe.utils.telemetry.capture") as sender, db_connections():
            with self.assertRaises(frappe.ValidationError):
                query.execute()
        return sender.call_args

    # @feature telemetry.query-failed
    def test_a_refused_run_reports_its_kind_its_interface_and_its_source(self):
        args, kwargs = self.refused_run()
        self.assertEqual(args, ("query_failed", "insights"))
        # the version and the cohort ride on every event and have their own test
        own = {k: v for k, v in kwargs["properties"].items() if k not in ("app_version", "entry")}
        self.assertEqual(
            own,
            {
                "interface": "builder",
                "error_kind": "refused",
                "data_store": False,
                "source_type": "site_db",
            },
        )

    # @feature telemetry.query-failed
    def test_a_report_names_nothing_the_query_reads(self):
        _, kwargs = self.refused_run()
        sent = frappe.as_json(kwargs["properties"])
        for secret in ("tabToDo", FIRST_TITLE, SECOND_TITLE, "SELECT", "Circular"):
            self.assertNotIn(secret, sent)
