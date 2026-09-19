import json
from unittest.mock import patch

import frappe

from insights.api.view import get_chart, get_chart_data, get_dashboard, get_filter_values
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.permission_user import permission_user, permission_user_for
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

OWNER = "view_api_owner@test.com"
# admitted by visibility, holds no Insights role at all - the desk reader this
# ticket is for
DESK_USER = "view_api_desk_user@test.com"
# holds an Insights role, but the owner's content never admits them
OUTSIDER = "view_api_outsider@test.com"
GUEST = "Guest"

WORKBOOK_TITLE = "View API Test Workbook"
DASHBOARD_TITLE = "View API Test Dashboard"

TODO_PREFIX = "View API Test"
OWNER_TODOS = [f"{TODO_PREFIX} owner 1", f"{TODO_PREFIX} owner 2"]

MISSING_REFERENCES = [
    "view_api_test_app/no_such_thing",
    "no-such-route",
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


def table_config():
    """A configured chart: one row per description, counted. The rows a chart
    draws follow from this alone — nothing else describes its query."""
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


class TestViewAPI(InsightsIntegrationTestCase):
    SAVEPOINT = "test_view_api"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cls.cleanup()

        create_user(OWNER, first_name="View", last_name="Owner", roles="Insights User")
        create_user(OUTSIDER, first_name="View", last_name="Outsider", roles="Insights User")
        create_user(DESK_USER, first_name="View", last_name="Desk User")

        for description in OWNER_TODOS:
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": description,
                    "allocated_to": OWNER,
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
        delete_users(OWNER, OUTSIDER, DESK_USER)

    # fixtures

    def make_content(self, visibility="Everyone", title=DASHBOARD_TITLE):
        """A dashboard the owner owns, with one chart and one filter linked to it."""
        with as_user(OWNER):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "View API Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "View API Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": table_config(),
                    # a chart of its own stays private: the dashboard's
                    # visibility is what has to reach it
                    "visibility": "Private",
                }
            ).insert()
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

    def ship(self, doc):
        doc.db_set("is_standard", 1, update_modified=False)
        return frappe.get_doc(doc.doctype, doc.name)

    def fetch_data(self, user, chart, dashboard=None, **kwargs):
        with as_user(user), db_connections():
            return get_chart_data(chart=chart, dashboard=dashboard, **kwargs)

    # the desk reader

    # @feature permissions.non-insights-user
    def test_a_reader_without_an_insights_role_reads_the_dashboard(self):
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

    # @feature permissions.non-insights-user
    def test_a_reader_without_an_insights_role_reads_a_chart_on_the_dashboard(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER):
            response = get_chart(chart=chart.name, dashboard=dashboard.name)

        self.assertEqual(response["name"], chart.name)
        self.assertEqual(response["chart_type"], "Table")
        self.assertFalse(response["can_write"])

    # @feature permissions.non-insights-user permissions.chart-apply-user-permissions
    def test_a_reader_without_an_insights_role_fetches_chart_data(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        # the rows the desk user sees are the owner's, because the chart says so
        chart.db_set("apply_user_permissions", 0, update_modified=False)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))
        self.assertIn("description", [column["name"] for column in result["columns"]])

    # @feature permissions.chart-apply-user-permissions
    def test_chart_data_stays_under_the_declared_permissions(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        self.assertTrue(chart.apply_user_permissions)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        # a checked box is the engine's native permission application, so a
        # roleless reader sees none of the owner's rows
        self.assertEqual(self.descriptions(result), [])

    # @feature charts.missing-slot-message
    def test_an_unconfigured_chart_says_so_instead_of_drawing_its_source(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("apply_user_permissions", 0, update_modified=False)
        # a table chart that names no rows. Falling back to the source query here
        # drew the raw table and called it the chart
        chart.db_set("config", frappe.as_json({"limit": 50}), update_modified=False)

        with self.assertRaises(frappe.ValidationError) as raised:
            self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        self.assertIn("is not configured", str(raised.exception))
        self.assertIn("Rows are required", str(raised.exception))

    # @feature charts.table-rows-columns-values
    def test_chart_data_follows_the_config_with_nothing_to_refresh(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("apply_user_permissions", 0, update_modified=False)

        self.assertEqual(
            self.descriptions(self.fetch_data(DESK_USER, chart.name, dashboard.name)), sorted(OWNER_TODOS)
        )

        # the config is the whole description of the query, so editing it is all
        # it takes — no builder session, no second document to keep in step
        config = table_config()
        config["rows"] = [{"column_name": "status", "dimension_name": "status", "data_type": "String"}]
        chart.db_set("config", frappe.as_json(config), update_modified=False)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name)

        self.assertEqual([column["name"] for column in result["columns"]], ["status", "count"])

    # @feature charts.dimension-grain
    def test_the_grain_a_date_column_is_grouped_by_comes_from_the_config(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("apply_user_permissions", 0, update_modified=False)

        config = table_config()
        config["rows"] = [
            {
                "column_name": "creation",
                "dimension_name": "creation",
                "data_type": "Datetime",
                "granularity": "month",
            }
        ]
        chart.db_set("config", frappe.as_json(config), update_modified=False)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name)

        self.assertEqual(result["granularity"], {"creation": "month"})

    # a linked chart

    # @feature permissions.chart-access-follows
    def test_a_chart_is_reached_through_the_dashboard_it_is_on(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER):
            self.assertEqual(get_chart(chart=chart.name, dashboard=dashboard.name)["name"], chart.name)
            # the grant sits on the document, not on the path taken to it, so
            # the same chart answers a standalone reference too
            self.assertEqual(get_chart(chart=chart.name)["name"], chart.name)

        # a private chart no readable dashboard links to stays not found
        with as_user(OWNER):
            orphan = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "View API Orphan Chart",
                    "workbook": chart.workbook,
                    "query": chart.query,
                    "chart_type": "Table",
                    "config": {},
                    "visibility": "Private",
                }
            ).insert()

        with as_user(DESK_USER), self.assertRaises(frappe.DoesNotExistError):
            get_chart(chart=orphan.name)

    # @feature permissions.denied-is-not-found
    def test_a_chart_that_is_not_on_the_dashboard_is_not_found(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        _, other_chart, _ = self.make_content(visibility="Everyone", title="View API Other Dashboard")

        with as_user(DESK_USER), self.assertRaises(frappe.DoesNotExistError):
            get_chart(chart=other_chart.name, dashboard=dashboard.name)

    # denial leaks nothing

    # @feature permissions.denied-is-not-found
    def test_an_outsider_gets_the_same_answer_as_a_missing_reference(self):
        _, chart, dashboard = self.make_content(visibility="Private")

        errors = []
        with as_user(OUTSIDER):
            for reference in [dashboard.name, dashboard.route, *MISSING_REFERENCES]:
                with self.assertRaises(frappe.DoesNotExistError) as raised:
                    get_dashboard(dashboard=reference)
                errors.append(raised.exception)

            for reference in [chart.name, *MISSING_REFERENCES]:
                with self.assertRaises(frappe.DoesNotExistError) as raised:
                    get_chart(chart=reference)
                errors.append(raised.exception)

                with self.assertRaises(frappe.DoesNotExistError) as raised:
                    get_chart_data(chart=reference)
                errors.append(raised.exception)

        self.assertEqual({type(error) for error in errors}, {frappe.DoesNotExistError})
        self.assertEqual(len({str(error) for error in errors}), 1)

    # @feature shared.dashboard-link shared.chart-on-public-dashboard
    def test_a_guest_reads_public_content_only(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(GUEST), self.assertRaises(frappe.DoesNotExistError):
            get_dashboard(dashboard=dashboard.name)

        dashboard.db_set("visibility", "Public", update_modified=False)

        with as_user(GUEST):
            self.assertEqual(get_dashboard(dashboard=dashboard.name)["name"], dashboard.name)
            self.assertEqual(get_chart(chart=chart.name, dashboard=dashboard.name)["name"], chart.name)

    # @feature dashboard.list
    def test_opening_a_dashboard_counts_as_a_view_for_every_reader(self):
        """What a reader saw last is the same question on every surface.

        A guest is counted too: every guest is one user, so their rows are a
        floor on public views, which is what `site_profile` reads them as.
        """
        _, _, dashboard = self.make_content(visibility="Public")

        with as_user(DESK_USER):
            get_dashboard(dashboard=dashboard.name)
        with as_user(GUEST):
            get_dashboard(dashboard=dashboard.name)

        readers = frappe.get_all(
            "View Log",
            filters={"reference_doctype": DT.DASHBOARD, "reference_name": dashboard.name},
            pluck="viewed_by",
        )
        self.assertEqual(sorted(readers), sorted([DESK_USER, GUEST]))

    # references

    # @feature shared.reference dashboard.route
    def test_a_dashboard_resolves_by_docname_and_route(self):
        _, _, dashboard = self.make_content(visibility="Everyone", title="View API Referenced Dashboard")

        with as_user(DESK_USER):
            for reference in (dashboard.name, dashboard.route):
                self.assertEqual(get_dashboard(dashboard=reference)["name"], dashboard.name)

        self.assertEqual(dashboard.route, "view-api-referenced-dashboard")

    # @feature shared.reference
    def test_a_chart_resolves_by_docname(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER):
            self.assertEqual(get_chart(chart=chart.name, dashboard=dashboard.name)["name"], chart.name)

    # capability flags

    # @feature dashboard.open-workbook
    def test_capability_flags_separate_a_reader_from_an_editor(self):
        _, _, dashboard = self.make_content(visibility="Everyone")

        with as_user(OWNER):
            response = get_dashboard(dashboard=dashboard.name)
        self.assertTrue(response["can_write"])
        self.assertFalse(response["can_copy"])

        with as_user(DESK_USER):
            response = get_dashboard(dashboard=dashboard.name)
        self.assertFalse(response["can_write"])
        self.assertFalse(response["can_copy"])

    # @feature dashboard.shipped-read-only
    def test_shipped_content_is_copied_not_edited(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        dashboard = self.ship(dashboard)

        # a developer-mode bench is the one place shipped content is editable,
        # and this is the answer for every other site
        with patch.dict(frappe.conf, {"developer_mode": 0}):
            with as_user(OWNER):
                response = get_dashboard(dashboard=dashboard.name)
            # the owner holds write rights, but shipped content is read-only here
            self.assertFalse(response["can_write"])
            self.assertTrue(response["can_copy"])

            # copying is an authoring action, so a roleless reader is not offered it
            with as_user(DESK_USER):
                response = get_dashboard(dashboard=dashboard.name)
            self.assertFalse(response["can_copy"])

    # the query never crosses the boundary

    # @feature permissions.view-sends-no-query
    def test_no_response_carries_the_query_behind_the_chart(self):
        query, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("apply_user_permissions", 0, update_modified=False)

        with as_user(DESK_USER):
            responses = [
                get_dashboard(dashboard=dashboard.name),
                get_chart(chart=chart.name, dashboard=dashboard.name),
            ]
        responses.append(self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True))

        for response in responses:
            serialized = json.dumps(response, default=str)
            for leak in ("operations", "raw_sql", "tabToDo", query.name, "links"):
                self.assertNotIn(leak, serialized, f"{leak} must not reach a view")
            self.assertNotIn("sql", response)

    # dashboard filters route server-side

    # @feature dashboard.filter-links
    def test_dashboard_filter_state_reaches_the_query(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("apply_user_permissions", 0, update_modified=False)

        result = self.fetch_data(
            DESK_USER,
            chart.name,
            dashboard.name,
            filters={"Description": {"operator": "contains", "value": "owner 1"}},
            force=True,
        )

        self.assertEqual(self.descriptions(result), [OWNER_TODOS[0]])

    # @feature dashboard.filter-links
    def test_a_filter_names_the_charts_it_changes(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER):
            response = get_dashboard(dashboard=dashboard.name)

        filter_item = next(item for item in response["items"] if item["type"] == "filter")
        # enough to refetch just those cards and to let an empty card blame the
        # filter, without saying which column it lands on
        self.assertEqual(filter_item["charts"], [chart.name])
        self.assertEqual(filter_item["filter_type"], "String")

    # @feature dashboard.filter-values
    def test_filter_values_come_from_the_linked_column(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("apply_user_permissions", 0, update_modified=False)

        with as_user(DESK_USER), db_connections():
            values = get_filter_values(dashboard=dashboard.name, filter_name="Description")
            searched = get_filter_values(
                dashboard=dashboard.name, filter_name="Description", search_term="owner 1"
            )

        self.assertEqual(sorted(values), sorted(OWNER_TODOS))
        self.assertEqual(searched, [OWNER_TODOS[0]])

    # @feature permissions.non-insights-user dashboard.filter-values
    def test_a_roleless_reader_reaches_what_the_authoring_endpoints_gate(self):
        """The `Insights User` check sits on the endpoint, not on the computation.

        A view needs the same two answers an authoring client asks for — how many
        rows are behind a number, and what values a column offers — and holds no
        Insights role to ask with.
        """
        query, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("apply_user_permissions", 0, update_modified=False)
        query_doc = frappe.get_doc(DT.QUERY, query.name)

        with as_user(DESK_USER), db_connections():
            values = get_filter_values(dashboard=dashboard.name, filter_name="Description")
            with permission_user(permission_user_for(frappe.get_doc(DT.CHART, chart.name))):
                count = query_doc.count_rows()

        self.assertEqual(sorted(values), sorted(OWNER_TODOS))
        self.assertEqual(count, len(OWNER_TODOS))

    # @feature permissions.non-insights-user
    def test_a_dashboard_filter_list_needs_no_insights_role(self):
        _, _, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER), db_connections():
            values = get_filter_values(dashboard=dashboard.name, filter_name="Description")

            # the dashboard's own method is the builder's, and it asks for read
            # on the query the filter lands on
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc(DT.DASHBOARD, dashboard.name).get_distinct_column_values("Description")

        # empty, not refused: the chart applies each reader's permissions, so a
        # reader is offered the values their own permissions reach
        self.assertEqual(values, [])

    # @feature permissions.authoring-needs-role permissions.non-insights-user
    def test_the_authoring_endpoints_still_refuse_a_user_without_the_role(self):
        query, _, _ = self.make_content(visibility="Everyone")
        query_doc = frappe.get_doc(DT.QUERY, query.name)

        with as_user(DESK_USER):
            with self.assertRaises(frappe.PermissionError):
                query_doc.get_count()
            with self.assertRaises(frappe.PermissionError):
                query_doc.get_distinct_column_values("description")

    # @feature permissions.denied-is-not-found
    def test_filter_values_answer_like_any_other_reference(self):
        _, _, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER), self.assertRaises(frappe.DoesNotExistError):
            get_filter_values(dashboard=dashboard.name, filter_name="No Such Filter")

        _, _, private = self.make_content(visibility="Private", title="View API Private Dashboard")

        with as_user(OUTSIDER), self.assertRaises(frappe.DoesNotExistError):
            get_filter_values(dashboard=private.name, filter_name="Description")

    # what an editor is told

    # @feature dashboard.open-workbook
    def test_only_an_editor_is_told_where_editing_happens(self):
        _, _, dashboard = self.make_content(visibility="Everyone")

        with as_user(OWNER):
            self.assertEqual(get_dashboard(dashboard=dashboard.name)["workbook"], dashboard.workbook)

        with as_user(DESK_USER):
            self.assertIsNone(get_dashboard(dashboard=dashboard.name)["workbook"])
