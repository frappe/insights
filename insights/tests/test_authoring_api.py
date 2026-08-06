import json

import frappe

from insights.api.authoring import get_chart_data as get_authoring_data
from insights.api.viewer import get_chart
from insights.api.viewer import get_chart_data as get_viewer_data
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

AUTHOR = "authoring_api_author@test.com"
# holds an Insights role, but none of the author's content
OUTSIDER = "authoring_api_outsider@test.com"
# in the chart's audience and holds no Insights role at all: a reader, not an author
READER = "authoring_api_reader@test.com"

WORKBOOK_TITLE = "Authoring API Test Workbook"
TODO_PREFIX = "Authoring API Test"
AUTHOR_TODOS = [f"{TODO_PREFIX} author 1", f"{TODO_PREFIX} author 2"]


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


def table_config():
    """One row per description, counted."""
    return {
        "limit": 50,
        "rows": [{"dimension_name": "description", "column_name": "description", "data_type": "String"}],
        "columns": [],
        "values": [
            {
                "measure_name": "count",
                "column_name": "name",
                "aggregation": "count",
                "data_type": "Integer",
            }
        ],
        "order_by": [],
    }


class TestAuthoringAPI(InsightsIntegrationTestCase):
    SAVEPOINT = "test_authoring_api"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cls.cleanup()

        create_user(AUTHOR, first_name="Authoring", last_name="Author", roles="Insights User")
        create_user(OUTSIDER, first_name="Authoring", last_name="Outsider", roles="Insights User")
        create_user(READER, first_name="Authoring", last_name="Reader")

        for description in AUTHOR_TODOS:
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": description,
                    "allocated_to": AUTHOR,
                    "assigned_by": "Administrator",
                }
            ).insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        cls.cleanup()
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.original_enable_permissions)

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for todo in frappe.get_all(
            "ToDo", filters={"description": ["like", f"%{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        delete_users(AUTHOR, OUTSIDER, READER)

    # fixtures

    def make_content(self):
        """A saved chart the author owns, and the query behind it."""
        with as_user(AUTHOR):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Authoring API Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Authoring API Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": table_config(),
                    # the author's own rows, so a reader sees the same numbers
                    "data_authority": "Author",
                    "visibility": "Everyone",
                }
            ).insert()

        return frappe.get_doc(DT.QUERY, query.name), frappe.get_doc(DT.CHART, chart.name)

    def preview(self, user, **kwargs):
        with as_user(user), db_connections():
            return get_authoring_data(**kwargs)

    def descriptions(self, result):
        return sorted(row["description"] for row in result["rows"])

    # the preview

    def test_a_config_that_was_never_saved_draws_rows(self):
        query, _ = self.make_content()

        result = self.preview(
            AUTHOR,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            force=True,
        )

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))
        self.assertEqual([column["name"] for column in result["columns"]], ["description", "count"])
        self.assertEqual(result["errors"], [])

    def test_the_preview_says_what_it_ran(self):
        query, _ = self.make_content()

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=table_config())

        # the operations the drill-down forks, and the SQL the author debugs
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "summarize"],
        )
        self.assertEqual(result["operations"][0]["table"]["query_name"], query.name)
        self.assertIn("select", result["sql"].lower())

    def test_the_preview_runs_what_the_saved_chart_would(self):
        query, chart = self.make_content()

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=table_config())

        # one deriver behind both doors, so what the author is shaping is what
        # every reader of the saved chart gets
        self.assertEqual(result["operations"], chart.get_operations())

    def test_a_half_configured_chart_says_what_is_missing(self):
        query, _ = self.make_content()
        config = table_config()
        config["rows"] = []

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=config)

        # the builder's normal state on the way to a chart: no rows, and no error
        # either — the card keeps the last picture and says what is still needed
        self.assertEqual(result["errors"], ["Rows are required"])
        self.assertNotIn("rows", result)

    def test_the_grain_comes_back_with_the_rows(self):
        query, _ = self.make_content()
        config = table_config()
        config["rows"] = [
            {
                "column_name": "creation",
                "dimension_name": "creation",
                "data_type": "Datetime",
                "granularity": "month",
            }
        ]

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=config)

        self.assertEqual(result["granularity"], {"creation": "month"})

    # the gate

    def test_a_reader_without_an_authoring_seat_is_refused(self):
        query, chart = self.make_content()
        self.assertNotIn("Insights User", frappe.get_roles(READER))

        # the reader may see the chart — it is the derivation behind it they may not
        with as_user(READER):
            self.assertEqual(get_chart(chart=chart.name)["name"], chart.name)

        with self.assertRaises(frappe.PermissionError):
            self.preview(READER, chart_type="Table", query=query.name, config=table_config())

    def test_a_query_the_caller_cannot_read_is_refused(self):
        query, chart = self.make_content()
        # naming a query is how this endpoint says what to run, so a seat alone is
        # not enough — the caller has to be able to read the query they name
        chart.db_set("visibility", "Private", update_modified=False)

        with self.assertRaises(frappe.PermissionError):
            self.preview(OUTSIDER, chart_type="Table", query=query.name, config=table_config())

    # the viewer contract is unchanged

    def test_no_viewer_response_carries_the_derived_operations(self):
        query, chart = self.make_content()

        with as_user(READER), db_connections():
            responses = [
                get_chart(chart=chart.name),
                get_viewer_data(chart=chart.name, force=True),
            ]

        for response in responses:
            serialized = json.dumps(response, default=str)
            for leak in ("operations", "summarize", "tabToDo", query.name):
                self.assertNotIn(leak, serialized, f"{leak} must not reach a viewer")
            self.assertNotIn("sql", response)
