import json
from unittest.mock import patch

import frappe

from insights.api.viewer import get_chart, get_chart_data, get_dashboard, get_filter_values
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.resolver import ContentNotAvailableError
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

AUTHOR = "viewer_api_author@test.com"
# in the audience, holds no Insights role at all - the desk viewer this ticket is for
DESK_USER = "viewer_api_desk_user@test.com"
# holds an Insights role but is in no audience of the author's content
OUTSIDER = "viewer_api_outsider@test.com"
GUEST = "Guest"

WORKBOOK_TITLE = "Viewer API Test Workbook"
DASHBOARD_TITLE = "Viewer API Test Dashboard"
SHIPPED_ID = "viewer_api_test_app/todo_overview"

TODO_PREFIX = "Viewer API Test"
AUTHOR_TODOS = [f"{TODO_PREFIX} author 1", f"{TODO_PREFIX} author 2"]

MISSING_REFERENCES = [
    "viewer_api_test_app/no_such_thing",
    "no-such-slug",
    "0123456789",
]


def todo_operations():
    """A query over `tabToDo`, narrowed to this module's fixtures."""
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


def chart_operations(query):
    """What a configured chart's data query holds: its source query, then the
    chart's own summarize. Nothing reads a chart off the source query."""
    return [
        {
            "type": "source",
            "table": {"type": "query", "query_name": query, "workbook": 0},
        },
        {
            "type": "summarize",
            "dimensions": [
                {"dimension_name": "description", "column_name": "description", "data_type": "String"}
            ],
            "measures": [
                {
                    "measure_name": "count",
                    "column_name": "name",
                    "aggregation": "count",
                    "data_type": "Integer",
                }
            ],
        },
    ]


class TestViewerAPI(InsightsIntegrationTestCase):
    SAVEPOINT = "test_viewer_api"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cls.cleanup()

        create_user(AUTHOR, first_name="Viewer", last_name="Author", roles="Insights User")
        create_user(OUTSIDER, first_name="Viewer", last_name="Outsider", roles="Insights User")
        create_user(DESK_USER, first_name="Viewer", last_name="Desk User")

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
        delete_users(AUTHOR, OUTSIDER, DESK_USER)

    # fixtures

    def make_content(self, visibility="Everyone", title=DASHBOARD_TITLE):
        """A dashboard the author owns, with one chart and one filter linked to it."""
        with as_user(AUTHOR):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Viewer API Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Viewer API Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": {"limit": 50, "rows": [{"column_name": "description"}]},
                    # a chart of its own stays private: the dashboard's audience
                    # is what has to carry it
                    "visibility": "Private",
                }
            ).insert()
            # the builder derives this the moment a chart is configured; a
            # fixture without it is an unconfigured chart, not a shortcut
            frappe.db.set_value(
                DT.QUERY,
                chart.data_query,
                {
                    "operations": frappe.as_json(chart_operations(query.name)),
                    "use_live_connection": 1,
                },
            )
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": title,
                    "workbook": workbook.name,
                    "visibility": visibility,
                    "items": [
                        {
                            "type": "chart",
                            "chart": chart.name,
                            "layout": {"i": "chart-1", "x": 0, "y": 1, "w": 10, "h": 8},
                        },
                        {
                            "type": "filter",
                            "filter_name": "Description",
                            "filter_type": "String",
                            "links": {chart.name: f"`{query.name}`.`description`"},
                            "layout": {"i": "filter-1", "x": 0, "y": 0, "w": 4, "h": 1},
                        },
                    ],
                }
            ).insert()

        return (
            frappe.get_doc(DT.QUERY, query.name),
            frappe.get_doc(DT.CHART, chart.name),
            frappe.get_doc(DT.DASHBOARD, dashboard.name),
        )

    def ship(self, doc, logical_id=SHIPPED_ID):
        doc.db_set("logical_id", logical_id, update_modified=False)
        doc.db_set("is_standard", 1, update_modified=False)
        return frappe.get_doc(doc.doctype, doc.name)

    def fetch_data(self, user, chart, dashboard=None, **kwargs):
        with as_user(user), db_connections():
            return get_chart_data(chart=chart, dashboard=dashboard, **kwargs)

    def descriptions(self, result):
        return sorted(row["description"] for row in result["rows"])

    # the desk viewer

    def test_audience_member_without_an_insights_role_reads_the_dashboard(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        self.assertNotIn("Insights User", frappe.get_roles(DESK_USER))

        with as_user(DESK_USER):
            response = get_dashboard(dashboard=dashboard.name)

        self.assertEqual(response["title"], DASHBOARD_TITLE)
        self.assertEqual(
            [item["type"] for item in response["items"]],
            ["chart", "filter"],
        )
        self.assertEqual(response["items"][0]["chart"], chart.name)
        self.assertEqual(response["items"][0]["layout"]["w"], 10)

    def test_audience_member_without_an_insights_role_reads_a_chart_on_the_dashboard(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER):
            response = get_chart(chart=chart.name, dashboard=dashboard.name)

        self.assertEqual(response["name"], chart.name)
        self.assertEqual(response["chart_type"], "Table")
        self.assertFalse(response["can_edit"])

    def test_audience_member_without_an_insights_role_fetches_chart_data(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        # the rows the desk user sees are the author's, because the chart says so
        chart.db_set("data_authority", "Author", update_modified=False)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))
        self.assertIn("description", [column["name"] for column in result["columns"]])

    def test_chart_data_stays_under_the_declared_authority(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        self.assertEqual(chart.data_authority, "Viewer")

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        # `Viewer` is the engine's native permission application, so a roleless
        # viewer sees none of the author's rows
        self.assertEqual(self.descriptions(result), [])

    def test_an_unconfigured_chart_says_so_instead_of_drawing_its_source(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("data_authority", "Author", update_modified=False)
        # a chart whose data query was never derived. Falling back to the source
        # query here drew the raw table and called it the chart
        frappe.db.set_value(DT.QUERY, chart.data_query, "operations", "[]")

        with self.assertRaises(frappe.ValidationError) as raised:
            self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        self.assertIn("no operations on its data query", str(raised.exception))

    # the cascade

    def test_a_chart_is_carried_by_the_dashboard_it_is_on(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER):
            self.assertEqual(get_chart(chart=chart.name, dashboard=dashboard.name)["name"], chart.name)
            # the cascade sits on the document, not on the path taken to it, so
            # the same chart answers a standalone reference too
            self.assertEqual(get_chart(chart=chart.name)["name"], chart.name)

        # a private chart no readable dashboard carries stays unavailable
        with as_user(AUTHOR):
            orphan = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Viewer API Orphan Chart",
                    "workbook": chart.workbook,
                    "query": chart.query,
                    "chart_type": "Table",
                    "config": {},
                    "visibility": "Private",
                }
            ).insert()

        with as_user(DESK_USER), self.assertRaises(ContentNotAvailableError):
            get_chart(chart=orphan.name)

    def test_a_chart_that_is_not_on_the_dashboard_is_not_available(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        _, other_chart, _ = self.make_content(visibility="Everyone", title="Viewer API Other Dashboard")

        with as_user(DESK_USER), self.assertRaises(ContentNotAvailableError):
            get_chart(chart=other_chart.name, dashboard=dashboard.name)

    # denial leaks nothing

    def test_an_outsider_gets_the_same_answer_as_a_missing_reference(self):
        _, chart, dashboard = self.make_content(visibility="Private")

        errors = []
        with as_user(OUTSIDER):
            for reference in [dashboard.name, dashboard.slug, *MISSING_REFERENCES]:
                with self.assertRaises(ContentNotAvailableError) as raised:
                    get_dashboard(dashboard=reference)
                errors.append(raised.exception)

            for reference in [chart.name, *MISSING_REFERENCES]:
                with self.assertRaises(ContentNotAvailableError) as raised:
                    get_chart(chart=reference)
                errors.append(raised.exception)

                with self.assertRaises(ContentNotAvailableError) as raised:
                    get_chart_data(chart=reference)
                errors.append(raised.exception)

        self.assertEqual({type(error) for error in errors}, {ContentNotAvailableError})
        self.assertEqual(len({str(error) for error in errors}), 1)

    def test_a_guest_reads_public_content_only(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(GUEST), self.assertRaises(ContentNotAvailableError):
            get_dashboard(dashboard=dashboard.name)

        dashboard.db_set("visibility", "Public", update_modified=False)

        with as_user(GUEST):
            self.assertEqual(get_dashboard(dashboard=dashboard.name)["name"], dashboard.name)
            self.assertEqual(get_chart(chart=chart.name, dashboard=dashboard.name)["name"], chart.name)

    # references

    def test_a_dashboard_resolves_by_docname_slug_and_logical_id(self):
        _, _, dashboard = self.make_content(visibility="Everyone", title="Viewer API Referenced Dashboard")
        dashboard = self.ship(dashboard)

        with as_user(DESK_USER):
            for reference in (dashboard.name, dashboard.slug, SHIPPED_ID):
                self.assertEqual(get_dashboard(dashboard=reference)["name"], dashboard.name)

        self.assertEqual(dashboard.slug, "viewer-api-referenced-dashboard")

    def test_a_chart_resolves_by_docname_and_logical_id(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart = self.ship(chart, logical_id="viewer_api_test_app/todo_chart")

        with as_user(DESK_USER):
            for reference in (chart.name, "viewer_api_test_app/todo_chart"):
                self.assertEqual(get_chart(chart=reference, dashboard=dashboard.name)["name"], chart.name)

    # capability flags

    def test_capability_flags_separate_a_viewer_from_an_editor(self):
        _, _, dashboard = self.make_content(visibility="Everyone")

        with as_user(AUTHOR):
            response = get_dashboard(dashboard=dashboard.name)
        self.assertTrue(response["can_edit"])
        self.assertFalse(response["can_duplicate"])

        with as_user(DESK_USER):
            response = get_dashboard(dashboard=dashboard.name)
        self.assertFalse(response["can_edit"])
        self.assertFalse(response["can_duplicate"])

    def test_shipped_content_is_duplicated_not_edited(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        dashboard = self.ship(dashboard)

        # a developer-mode bench is the one place shipped content is editable,
        # and this is the answer for every other site
        with patch.dict(frappe.conf, {"developer_mode": 0}):
            with as_user(AUTHOR):
                response = get_dashboard(dashboard=dashboard.name)
            # the author holds write rights, but shipped content is read-only here
            self.assertFalse(response["can_edit"])
            self.assertTrue(response["can_duplicate"])

            # duplicating is an authoring action, so a roleless viewer is not offered it
            with as_user(DESK_USER):
                response = get_dashboard(dashboard=dashboard.name)
            self.assertFalse(response["can_duplicate"])

    # the query never crosses the boundary

    def test_no_response_carries_the_query_behind_the_chart(self):
        query, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("data_authority", "Author", update_modified=False)

        with as_user(DESK_USER):
            responses = [
                get_dashboard(dashboard=dashboard.name),
                get_chart(chart=chart.name, dashboard=dashboard.name),
            ]
        responses.append(self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True))

        for response in responses:
            serialized = json.dumps(response, default=str)
            for leak in ("operations", "raw_sql", "tabToDo", query.name, "links"):
                self.assertNotIn(leak, serialized, f"{leak} must not reach a viewer")
            self.assertNotIn("sql", response)

    # dashboard filters route server-side

    def test_dashboard_filter_state_reaches_the_query(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("data_authority", "Author", update_modified=False)

        result = self.fetch_data(
            DESK_USER,
            chart.name,
            dashboard.name,
            filters={"Description": {"operator": "contains", "value": "author 1"}},
            force=True,
        )

        self.assertEqual(self.descriptions(result), [AUTHOR_TODOS[0]])

    def test_a_filter_names_the_charts_it_changes(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER):
            response = get_dashboard(dashboard=dashboard.name)

        filter_item = next(item for item in response["items"] if item["type"] == "filter")
        # enough to refetch just those cards and to let an empty card blame the
        # filter, without saying which column it lands on
        self.assertEqual(filter_item["charts"], [chart.name])
        self.assertEqual(filter_item["filter_type"], "String")

    def test_filter_values_come_from_the_linked_column(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("data_authority", "Author", update_modified=False)

        with as_user(DESK_USER), db_connections():
            values = get_filter_values(dashboard=dashboard.name, filter_name="Description")
            searched = get_filter_values(
                dashboard=dashboard.name, filter_name="Description", search_term="author 1"
            )

        self.assertEqual(sorted(values), sorted(AUTHOR_TODOS))
        self.assertEqual(searched, [AUTHOR_TODOS[0]])

    def test_filter_values_answer_like_any_other_reference(self):
        _, _, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER), self.assertRaises(ContentNotAvailableError):
            get_filter_values(dashboard=dashboard.name, filter_name="No Such Filter")

        _, _, private = self.make_content(visibility="Private", title="Viewer API Private Dashboard")

        with as_user(OUTSIDER), self.assertRaises(ContentNotAvailableError):
            get_filter_values(dashboard=private.name, filter_name="Description")

    # what an editor is told

    def test_only_an_editor_is_told_where_editing_happens(self):
        _, _, dashboard = self.make_content(visibility="Everyone")

        with as_user(AUTHOR):
            self.assertEqual(get_dashboard(dashboard=dashboard.name)["workbook"], dashboard.workbook)

        with as_user(DESK_USER):
            self.assertIsNone(get_dashboard(dashboard=dashboard.name)["workbook"])
