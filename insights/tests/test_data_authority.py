from contextlib import contextmanager
from unittest.mock import patch

import frappe
import ibis

from insights.api import run_doc_method as insights_run_doc_method
from insights.api.workbooks import update_share_permissions
from insights.insights.doctype.insights_data_source_v3.data_authority import (
    data_authority_of,
    get_authority_user,
    get_authority_user_for,
)
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_table_v3.insights_table_v3 import apply_user_permissions
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

AUTHOR = "data_authority_author@test.com"
VIEWER = "data_authority_viewer@test.com"

WORKBOOK_TITLE = "Data Authority Test Workbook"
TODO_PREFIX = "Data Authority Test"

AUTHOR_TODOS = [f"{TODO_PREFIX} author 1", f"{TODO_PREFIX} author 2"]
VIEWER_TODOS = [f"{TODO_PREFIX} viewer 1"]

TEST_DS_TITLE = "Data Authority Test DuckDB"
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


class TestDataAuthority(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.cleanup()
        create_user(AUTHOR, first_name="Data", last_name="Author", roles="Insights User")
        create_user(VIEWER, first_name="Data", last_name="Viewer", roles="Insights User")

        for user, descriptions in ((AUTHOR, AUTHOR_TODOS), (VIEWER, VIEWER_TODOS)):
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
                "database_name": "data_authority_test_duckdb",
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
        delete_users(AUTHOR, VIEWER)

    @classmethod
    def create_content(cls):
        """A chart owned by AUTHOR, readable by VIEWER through a read-only share."""
        with as_user(AUTHOR):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Data Authority Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Data Authority Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": {},
                }
            ).insert()
            update_share_permissions(workbook.name, [{"user": VIEWER, "read": 1, "write": 0}])

        # the chart's own data query mirrors the source query, which is what the
        # frontend persists once a chart is configured
        frappe.db.set_value(
            DT.QUERY,
            chart.data_query,
            {"operations": frappe.as_json(todo_operations()), "use_live_connection": 1},
        )

        return workbook, query, frappe.get_doc(DT.CHART, chart.name)

    def set_authority(self, authority):
        frappe.db.set_value(DT.CHART, self.chart.name, "data_authority", authority)
        self.addCleanup(frappe.db.set_value, DT.CHART, self.chart.name, "data_authority", "Viewer")

    def descriptions(self, result):
        return sorted(row["description"] for row in result["rows"])

    def fetch_chart_data(self, user):
        with as_user(user), db_connections():
            return frappe.get_doc(DT.CHART, self.chart.name).get_data(force=True)

    def test_default_authority_is_viewer(self):
        chart = frappe.get_doc(DT.CHART, self.chart.name)
        self.assertEqual(chart.data_authority, "Viewer")

        with as_user(VIEWER):
            self.assertEqual(get_authority_user_for(DT.CHART, chart.name), VIEWER)

    def test_viewer_authority_filters_rows_per_session_user(self):
        self.set_authority("Viewer")

        author_rows = self.descriptions(self.fetch_chart_data(AUTHOR))
        viewer_rows = self.descriptions(self.fetch_chart_data(VIEWER))

        self.assertEqual(author_rows, sorted(AUTHOR_TODOS))
        self.assertEqual(viewer_rows, sorted(VIEWER_TODOS))
        self.assertNotEqual(author_rows, viewer_rows)

    def test_author_authority_applies_owner_permissions_without_switching_session_user(self):
        self.set_authority("Author")

        with as_user(VIEWER), db_connections():
            chart = frappe.get_doc(DT.CHART, self.chart.name)
            # the escalation must come from the declaration alone, never from
            # impersonating the author for the rest of the request
            with patch.object(frappe, "set_user", side_effect=AssertionError("set_user in a request")):
                result = chart.get_data(force=True)

            self.assertEqual(frappe.session.user, VIEWER)
            self.assertEqual(get_authority_user(), VIEWER)

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))

    def test_request_payload_cannot_flip_declared_authority(self):
        self.set_authority("Viewer")

        forged = frappe.get_doc(DT.CHART, self.chart.name).as_dict()
        forged.update({"data_authority": "Author", "owner": AUTHOR})

        with as_user(VIEWER), db_connections(), as_http_request():
            result = insights_run_doc_method(
                method="get_data",
                docs=frappe.as_json(forged),
                args={"force": True},
            )

        self.assertEqual(self.descriptions(result), sorted(VIEWER_TODOS))

        # the seam reads the declaration off the stored document, so it holds even
        # when it is handed a document built out of the request payload
        with as_user(VIEWER), data_authority_of(frappe.get_doc(forged)) as authority_user:
            self.assertEqual(authority_user, VIEWER)

    def test_request_argument_cannot_flip_declared_authority(self):
        self.set_authority("Viewer")

        docs = frappe.as_json({"doctype": DT.CHART, "name": self.chart.name})

        with as_user(VIEWER), db_connections(), as_http_request():
            result = insights_run_doc_method(
                method="get_data",
                docs=docs,
                args={"force": True, "data_authority": "Author", "user": AUTHOR},
            )

        self.assertEqual(self.descriptions(result), sorted(VIEWER_TODOS))

        # frappe's own dispatcher passes arguments straight through, so an unknown
        # one is rejected rather than silently dropped
        with as_user(VIEWER), db_connections(), as_http_request():
            with self.assertRaises(TypeError):
                frappe.handler.run_doc_method(
                    method="get_data",
                    dt=DT.CHART,
                    dn=self.chart.name,
                    args={"data_authority": "Author"},
                )

    def test_forged_data_query_cannot_run_under_the_author(self):
        """The chart names the query too — a payload cannot point it elsewhere."""
        self.set_authority("Author")

        with as_user(AUTHOR):
            other = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Data Authority Test Other Query",
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
        forged.update({"data_query": other.name, "query": other.name})

        with as_user(VIEWER), db_connections(), as_http_request():
            result = insights_run_doc_method(
                method="get_data",
                docs=frappe.as_json(forged),
                args={"force": True},
            )

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))

    def test_non_site_db_rows_are_unfiltered_under_both_authorities(self):
        """External sources carry no Frappe permissions, so neither mode filters them."""
        table = ibis.memtable({"name": ["a", "b"], "value": [1, 2]})

        for user in (AUTHOR, VIEWER):
            with self.subTest(user=user):
                self.assertIs(apply_user_permissions(table, TEST_DS, "table1", user=user), table)
