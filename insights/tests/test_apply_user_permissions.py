from contextlib import contextmanager
from unittest.mock import patch

import frappe
import ibis

from insights.api import run_doc_method as insights_run_doc_method
from insights.api.workbooks import update_share_permissions
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    apply_user_permissions as filter_rows_for,
)
from insights.permission_user import get_permission_user, permission_user_for
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

OWNER = "apply_user_permissions_owner@test.com"
READER = "apply_user_permissions_reader@test.com"

WORKBOOK_TITLE = "Apply User Permissions Test Workbook"
TODO_PREFIX = "Apply User Permissions Test"

OWNER_TODOS = [f"{TODO_PREFIX} owner 1", f"{TODO_PREFIX} owner 2"]
READER_TODOS = [f"{TODO_PREFIX} reader 1"]

TEST_DS_TITLE = "Apply User Permissions Test DuckDB"
TEST_DS = frappe.scrub(TEST_DS_TITLE)


@contextmanager
def as_http_request():
    """`insights.api.run_doc_method` validates the HTTP method, so fake a request."""
    frappe.local.request = frappe._dict(method="POST", headers={})
    try:
        yield
    finally:
        del frappe.local.request


def todo_operations():
    """A query over `tabToDo`, narrowed to this module's fixtures.

    ToDo's permission query restricts non-System-Manager users to their own
    assignments, which is the row-level difference these tests turn on.
    """
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


class TestApplyUserPermissions(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.cleanup()
        create_user(OWNER, first_name="Permissions", last_name="Owner", roles="Insights User")
        create_user(READER, first_name="Permissions", last_name="Reader", roles="Insights User")

        for user, descriptions in ((OWNER, OWNER_TODOS), (READER, READER_TODOS)):
            for description in descriptions:
                frappe.get_doc(
                    {
                        "doctype": "ToDo",
                        "description": description,
                        "allocated_to": user,
                        "assigned_by": "Administrator",
                    }
                ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": DT.DATA_SOURCE,
                "title": TEST_DS_TITLE,
                "database_type": "DuckDB",
                "database_name": "apply_user_permissions_test_duckdb",
            }
        ).insert()

        cls.workbook, cls.query, cls.chart = cls.create_content()

    @classmethod
    def after_class(cls):
        cls.cleanup()

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for todo in frappe.get_all(
            "ToDo", filters={"description": ["like", f"%{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        if frappe.db.exists(DT.DATA_SOURCE, TEST_DS):
            frappe.delete_doc(DT.DATA_SOURCE, TEST_DS, force=True)
        delete_users(OWNER, READER)

    @classmethod
    def create_content(cls):
        """A chart owned by OWNER, readable by READER through a read-only share."""
        with as_user(OWNER):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Apply User Permissions Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Apply User Permissions Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    # one row per description, which is the column these tests read
                    "config": {
                        "rows": [
                            {
                                "column_name": "description",
                                "dimension_name": "description",
                                "data_type": "String",
                            }
                        ],
                        "columns": [],
                        "values": [],
                        "order_by": [],
                    },
                }
            ).insert()
            update_share_permissions(workbook.name, [{"user": READER, "read": 1, "write": 0}])

        return workbook, query, frappe.get_doc(DT.CHART, chart.name)

    def set_apply_user_permissions(self, value):
        frappe.db.set_value(DT.CHART, self.chart.name, "apply_user_permissions", value)
        self.addCleanup(frappe.db.set_value, DT.CHART, self.chart.name, "apply_user_permissions", 1)

    def fetch_chart_data(self, user):
        with as_user(user), db_connections():
            return frappe.get_doc(DT.CHART, self.chart.name).get_data(force=True)

    # @feature permissions.chart-apply-user-permissions
    def test_the_box_is_checked_by_default(self):
        chart = frappe.get_doc(DT.CHART, self.chart.name)
        self.assertTrue(chart.apply_user_permissions)

        with as_user(READER):
            self.assertEqual(permission_user_for(frappe.get_doc(DT.CHART, chart.name)), READER)

    # @feature permissions.chart-apply-user-permissions
    def test_a_checked_box_filters_rows_per_session_user(self):
        self.set_apply_user_permissions(1)

        owner_rows = self.descriptions(self.fetch_chart_data(OWNER))
        reader_rows = self.descriptions(self.fetch_chart_data(READER))

        self.assertEqual(owner_rows, sorted(OWNER_TODOS))
        self.assertEqual(reader_rows, sorted(READER_TODOS))
        self.assertNotEqual(owner_rows, reader_rows)

    # @feature permissions.chart-apply-user-permissions
    def test_an_unchecked_box_applies_owner_permissions_without_switching_session_user(self):
        self.set_apply_user_permissions(0)

        with as_user(READER), db_connections():
            chart = frappe.get_doc(DT.CHART, self.chart.name)
            # the escalation must come from the declaration alone, never from
            # impersonating the owner for the rest of the request
            with patch.object(frappe, "set_user", side_effect=AssertionError("set_user in a request")):
                result = chart.get_data(force=True)

            self.assertEqual(frappe.session.user, READER)
            self.assertEqual(get_permission_user(), READER)

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))

    # @feature shared.rows-are-the-owners
    def test_a_guest_reads_a_public_chart_as_its_owner(self):
        """Guests have no permissions, so the widest level draws the owner's rows."""
        self.addCleanup(
            frappe.db.set_value,
            DT.CHART,
            self.chart.name,
            {"visibility": "Private", "apply_user_permissions": 1},
        )
        with as_user(OWNER):
            chart = frappe.get_doc(DT.CHART, self.chart.name)
            chart.visibility = "Public"
            chart.save()

        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart.name, "apply_user_permissions"))
        self.assertEqual(self.descriptions(self.fetch_chart_data("Guest")), sorted(OWNER_TODOS))

    # @feature permissions.chart-apply-user-permissions permissions.request-body-not-trusted
    def test_request_payload_cannot_flip_the_declaration(self):
        self.set_apply_user_permissions(1)

        forged = frappe.get_doc(DT.CHART, self.chart.name).as_dict()
        forged.update({"apply_user_permissions": 0, "owner": OWNER})

        with as_user(READER), db_connections(), as_http_request():
            result = insights_run_doc_method(
                method="get_data",
                docs=frappe.as_json(forged),
                args={"force": True},
            )

        self.assertEqual(self.descriptions(result), sorted(READER_TODOS))

        # the seam reads the declaration off the stored document, so it holds even
        # when it is handed a document built out of the request payload
        with as_user(READER):
            self.assertEqual(permission_user_for(frappe.get_doc(forged)), READER)

    # @feature permissions.chart-apply-user-permissions permissions.request-body-not-trusted
    def test_request_argument_cannot_flip_the_declaration(self):
        self.set_apply_user_permissions(1)

        docs = frappe.as_json({"doctype": DT.CHART, "name": self.chart.name})

        with as_user(READER), db_connections(), as_http_request():
            result = insights_run_doc_method(
                method="get_data",
                docs=docs,
                args={"force": True, "apply_user_permissions": 0, "user": OWNER},
            )

        self.assertEqual(self.descriptions(result), sorted(READER_TODOS))

        # frappe's own dispatcher passes arguments straight through, so an unknown
        # one is rejected rather than silently dropped
        with as_user(READER), db_connections(), as_http_request():
            with self.assertRaises(TypeError):
                frappe.handler.run_doc_method(
                    method="get_data",
                    dt=DT.CHART,
                    dn=self.chart.name,
                    args={"apply_user_permissions": 0},
                )

    # @feature permissions.chart-apply-user-permissions permissions.request-body-not-trusted
    def test_a_forged_query_reference_cannot_run_under_the_owner(self):
        """The chart names the query too — a payload cannot point it elsewhere."""
        self.set_apply_user_permissions(0)

        with as_user(OWNER):
            other = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Apply User Permissions Test Other Query",
                    "workbook": self.workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": [
                        {
                            "type": "source",
                            "table": {
                                "type": "table",
                                "data_source": "Site DB",
                                "table_name": "tabUser",
                            },
                        }
                    ],
                }
            ).insert()

        forged = frappe.get_doc(DT.CHART, self.chart.name).as_dict()
        forged.update({"query": other.name})

        with as_user(READER), db_connections(), as_http_request():
            result = insights_run_doc_method(
                method="get_data",
                docs=frappe.as_json(forged),
                args={"force": True},
            )

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))

    # @feature permissions.chart-apply-user-permissions permissions.site-user-permissions
    def test_non_site_db_rows_are_unfiltered_either_way(self):
        """External sources carry no Frappe permissions, so neither mode filters them."""
        table = ibis.memtable({"name": ["a", "b"], "value": [1, 2]})

        for user in (OWNER, READER):
            with self.subTest(user=user):
                self.assertIs(filter_rows_for(table, TEST_DS, "table1", user=user), table)
