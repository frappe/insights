"""A native query is bounded before it reaches the SQL parser.

`sqlparse` groups comments in quadratic time, so input written to be slow holds
a synchronous worker for seconds of pure CPU with no data source involved. Both
routes into a native query — the format button and execution — parse the same
text, so both read the same bound.
"""

import frappe
from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    MAX_NATIVE_SQL_LENGTH,
    validate_native_sql_length,
)
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_workbook, delete_users
from insights.tests.permissions_utils import USER_1, create_test_users


class TestNativeSQLLength(UnitTestCase):
    def test_an_ordinary_statement_passes(self):
        validate_native_sql_length("select name from tabToDo where status = 'Open'")

    def test_no_sql_passes(self):
        validate_native_sql_length(None)
        validate_native_sql_length("")

    def test_a_statement_at_the_bound_passes(self):
        validate_native_sql_length("-" * MAX_NATIVE_SQL_LENGTH)

    def test_a_statement_over_the_bound_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            validate_native_sql_length("-- c\n" * MAX_NATIVE_SQL_LENGTH)


class TestBothRoutesReadTheBound(InsightsIntegrationTestCase):
    OVERSIZE = "-- c\n" * MAX_NATIVE_SQL_LENGTH

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(USER_1, title="Native SQL Workbook").name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(USER_1)

    def native_query(self, raw_sql):
        with self.as_user(USER_1):
            return frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Native SQL Query",
                    "workbook": self.workbook,
                    "use_live_connection": 1,
                    "is_native_query": 1,
                    "operations": [
                        {"type": "sql", "data_source": "Site DB", "raw_sql": raw_sql},
                    ],
                }
            ).insert()

    def test_the_format_button_refuses_an_oversize_statement(self):
        doc = self.native_query("select 1")
        self.addCleanup(frappe.delete_doc, DT.QUERY, doc.name, force=True, ignore_permissions=True)
        with self.as_user(USER_1), self.assertRaisesRegex(frappe.ValidationError, "limited to"):
            doc.format(self.OVERSIZE)

    def test_executing_an_oversize_statement_is_refused(self):
        """Refused for its length, before the parser sees it. Oversize SQL is
        rejected either way — the point is that the parser never runs."""
        doc = self.native_query(self.OVERSIZE)
        self.addCleanup(frappe.delete_doc, DT.QUERY, doc.name, force=True, ignore_permissions=True)
        with (
            self.as_user(USER_1),
            self.assertRaisesRegex(frappe.ValidationError, "limited to"),
            db_connections(),
        ):
            doc.execute()
