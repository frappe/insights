import json
from unittest.mock import patch

import frappe

from insights.api.view import (
    download_chart_rows,
    get_chart,
    get_chart_count,
    get_chart_data,
    get_dashboard,
    get_filter_values,
)
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.not_permitted import NotPermitted
from insights.permission_user import permission_user, permission_user_for
from insights.resolver import may_read
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
                    # a Public dashboard carries only charts that run as their owner
                    "run_as_owner": int(visibility == "Public"),
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
        """As an import leaves it: the workbook row says the content is shipped."""
        frappe.db.set_value(DT.WORKBOOK, doc.workbook, "is_standard", 1, update_modified=False)
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

    # @feature permissions.denied-is-not-found
    def test_a_dashboard_hands_over_only_the_charts_this_reader_may_read(self):
        """A dashboard's level reaches every chart on it, and a User Permission
        still narrows the reader: one on the query the first chart reads refuses
        the second, and a title and a rendering config are that chart being
        read."""
        _, chart, dashboard = self.make_content(visibility="Everyone")
        elsewhere = self.make_second_chart(dashboard)
        self.narrow_to_query(DESK_USER, chart.query)

        with as_user(DESK_USER):
            response = get_dashboard(dashboard=dashboard.name)
            # the card itself is refused, which is the answer this one agrees with
            with self.assertRaises(frappe.DoesNotExistError):
                get_chart(chart=elsewhere.name, dashboard=dashboard.name)

        self.assertEqual([drawn["name"] for drawn in response["charts"]], [chart.name])
        # and the cell goes with the chart: a cell naming a chart that is not in
        # `charts` draws "Chart not found", and the docname of refused content
        # crossing the wire is the content being read - after a workbook is
        # shipped the docname *is* the title in readable form
        named = [item.get("chart") for item in response["items"] if item["type"] == "chart"]
        self.assertEqual(named, [chart.name])
        self.assertNotIn(elsewhere.name, frappe.as_json(response))

    # @feature permissions.denied-is-not-found
    def test_a_dashboard_with_no_chart_this_reader_may_read_is_not_found(self):
        """Not Found is the one answer for content a reader may not read. A wall
        of "Chart not found" is not one of the card's states."""
        _, chart, dashboard = self.make_content(visibility="Everyone")
        elsewhere = self.make_second_chart(dashboard)

        # the grid names one chart, and it reads a query this reader is
        # narrowed away from
        with as_user(OWNER):
            doc = frappe.get_doc(DT.DASHBOARD, dashboard.name)
            doc.items = [
                item
                for item in frappe.parse_json(doc.items)
                if item.get("chart") != chart.name and item.get("type") != "filter"
            ]
            doc.save()

        self.narrow_to_query(DESK_USER, chart.query)

        with as_user(DESK_USER):
            self.assertTrue(may_read(frappe.get_doc(DT.DASHBOARD, dashboard.name)))
            self.assertFalse(may_read(frappe.get_doc(DT.CHART, elsewhere.name)))
            with self.assertRaises(frappe.DoesNotExistError):
                get_dashboard(dashboard=dashboard.name)

    # @feature permissions.denied-is-not-found
    def test_a_dashboard_whose_charts_are_gone_opens_for_its_author(self):
        """A chart that no longer exists is not a chart this reader was refused.
        Before a chart's delete took its cells off, a delete left the cell
        naming it."""
        _, chart, dashboard = self.make_content(visibility="Private")
        elsewhere = self.make_second_chart(dashboard)

        with as_user(OWNER):
            doc = frappe.get_doc(DT.DASHBOARD, dashboard.name)
            doc.items = [
                item
                for item in frappe.parse_json(doc.items)
                if item.get("chart") != chart.name and item.get("type") != "filter"
            ]
            doc.save()
        # gone the way a delete left it before
        frappe.db.delete(DT.CHART, elsewhere.name)

        with as_user(OWNER):
            response = get_dashboard(dashboard=dashboard.name)

        self.assertEqual(response["charts"], [])
        self.assertEqual([item["type"] for item in response["items"]], [])

    def make_second_chart(self, dashboard):
        """A second chart for `dashboard`, over a query of its own."""
        with as_user(OWNER):
            workbook = frappe.get_doc(DT.WORKBOOK, dashboard.workbook)
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "View API Test Elsewhere Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "View API Test Elsewhere Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": table_config(),
                    "visibility": "Private",
                }
            ).insert()
            doc = frappe.get_doc(DT.DASHBOARD, dashboard.name)
            doc.items = [
                *frappe.parse_json(doc.items),
                {
                    "type": "chart",
                    "chart": chart.name,
                    "layout": {"i": "chart-2", "x": 0, "y": 9, "w": 10, "h": 8},
                },
            ]
            doc.save()

        return frappe.get_doc(DT.CHART, chart.name)

    def narrow_to_query(self, user, query):
        permission = frappe.get_doc(
            {"doctype": "User Permission", "user": user, "allow": DT.QUERY, "for_value": query}
        ).insert(ignore_permissions=True)
        # the savepoint rolls the row back before any cleanup runs, and the
        # rollback leaves the user's cached permissions in place
        self.addCleanup(frappe.cache.hdel, "user_permissions", user)
        self.addCleanup(
            frappe.delete_doc, "User Permission", permission.name, force=True, ignore_permissions=True
        )

    # @feature permissions.non-insights-user
    def test_a_reader_without_an_insights_role_reads_a_chart_on_the_dashboard(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(DESK_USER):
            response = get_chart(chart=chart.name, dashboard=dashboard.name)

        self.assertEqual(response["name"], chart.name)
        self.assertEqual(response["chart_type"], "Table")
        self.assertFalse(response["can_write"])

    # @feature permissions.non-insights-user permissions.chart-run-as-owner
    def test_a_reader_without_an_insights_role_fetches_chart_data(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        # the rows the desk user sees are the owner's, because the chart says so
        chart.db_set("run_as_owner", 1, update_modified=False)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))
        self.assertIn("description", [column["name"] for column in result["columns"]])

    # @feature permissions.chart-run-as-owner
    def test_chart_data_stays_under_the_declared_permissions(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        self.assertFalse(chart.run_as_owner)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        # an unchecked box is the engine's native permission application, so a
        # roleless reader sees none of the owner's rows
        self.assertEqual(self.descriptions(result), [])

    # @feature charts.missing-slot-message
    def test_an_unconfigured_chart_says_so_instead_of_drawing_its_source(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("run_as_owner", 1, update_modified=False)
        # a table chart that names no rows. Falling back to the source query here
        # drew the raw table and called it the chart
        chart.db_set("config", frappe.as_json({"limit": 50}), update_modified=False)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        # what is missing, as the builder says it, and no rows
        self.assertEqual(result["errors"], ["Rows are required"])
        self.assertNotIn("rows", result)

    # @feature charts.table-rows-columns-values
    def test_chart_data_follows_the_config_with_nothing_to_refresh(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("run_as_owner", 1, update_modified=False)

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
        chart.db_set("run_as_owner", 1, update_modified=False)

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

        # saved and not written: the save is what refuses a chart that runs as
        # its reader, and a guest applying their own would read an empty page
        with as_user(OWNER):
            chart.run_as_owner = 1
            chart.save()
            dashboard.visibility = "Public"
            dashboard.save()

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
            self.assertIsNone(response["workbook"])

    # @feature standard.duplicate
    def test_shipped_content_is_not_offered_for_copying_without_workbook_read(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        dashboard = self.ship(dashboard)

        with patch.dict(frappe.conf, {"developer_mode": 0}), as_user(OUTSIDER):
            self.assertFalse(frappe.has_permission(DT.WORKBOOK, "read", dashboard.workbook))
            response = get_dashboard(dashboard=dashboard.name)
            self.assertFalse(response["can_copy"])
            self.assertIsNone(response["workbook"])

    # @feature standard.duplicate
    def test_a_shipped_workbook_is_offered_for_copying_and_the_copy_is_the_sites(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        dashboard = self.ship(dashboard)

        with patch.dict(frappe.conf, {"developer_mode": 0}), as_user(OWNER):
            response = get_dashboard(dashboard=dashboard.name)
            self.assertEqual(response["workbook"], dashboard.workbook)

            workbook = frappe.get_doc(DT.WORKBOOK, dashboard.workbook).as_dict()
            self.assertTrue(workbook.read_only)
            self.assertTrue(workbook.can_copy)

            copy = frappe.get_doc(DT.WORKBOOK, frappe.get_doc(DT.WORKBOOK, dashboard.workbook).duplicate())
            self.assertFalse(copy.is_standard)
            self.assertFalse(copy.as_dict().read_only)

    # the query never crosses the boundary

    # @feature permissions.view-sends-no-query
    def test_no_response_carries_the_query_behind_the_chart(self):
        query, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("run_as_owner", 1, update_modified=False)

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

    # @feature charts.one-snapshot
    def test_the_rows_arrive_with_the_chart_they_were_computed_from(self):
        """`makeSavedChartView`'s load draws the `chart` this answer carries in the
        same step as its rows, so a card never holds a definition its rows do not
        answer. The chart is edited between two unforced reads, as an author in
        another tab would."""
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("run_as_owner", 1, update_modified=False)

        first = self.fetch_data(DESK_USER, chart.name, dashboard.name)
        self.assertEqual(first["chart"]["title"], "View API Test Chart")
        self.assertEqual(first["chart"]["config"]["limit"], 50)
        self.assertEqual(len(first["rows"]), len(OWNER_TODOS))

        with as_user(OWNER):
            edited = frappe.get_doc(DT.CHART, chart.name)
            config = frappe.parse_json(edited.config)
            config["limit"] = 1
            edited.config = config
            edited.title = "Top Description"
            edited.save()

        second = self.fetch_data(DESK_USER, chart.name, dashboard.name)
        self.assertEqual(second["chart"]["title"], "Top Description")
        self.assertEqual(second["chart"]["config"]["limit"], 1)
        self.assertEqual(len(second["rows"]), 1)
        # the version a drill from this card carries back
        self.assertEqual(
            second["chart"]["modified"], str(frappe.db.get_value(DT.CHART, chart.name, "modified"))
        )

    # dashboard filters route server-side

    # @feature dashboard.filter-links
    def test_dashboard_filter_state_reaches_the_query(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("run_as_owner", 1, update_modified=False)

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
        chart.db_set("run_as_owner", 1, update_modified=False)

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
        chart.db_set("run_as_owner", 1, update_modified=False)
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

        # empty, not refused: the chart applies each reader's permissions, so a
        # reader is offered the values their own permissions reach
        self.assertEqual(values, [])

    # @feature permissions.request-body-not-trusted
    def test_a_reader_cannot_supply_the_routing_table(self):
        """`run_doc_method` builds the document from the request body, so the
        grid in hand is the caller's. A forged link would narrow a published
        filter's list by a column nobody published."""
        query, chart, dashboard = self.make_content(visibility="Everyone")
        # runs as its owner, so the reader sees a list to narrow in the first place
        frappe.db.set_value(DT.CHART, chart.name, "run_as_owner", 1, update_modified=False)

        forged = frappe.get_doc(DT.DASHBOARD, dashboard.name)
        forged.items = [
            *frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items")),
            {
                "id": "forged",
                "type": "filter",
                "filter_name": "Forged",
                "filter_type": "String",
                # `status` is on the query and on no filter the author published
                "links": {chart.name: f"`{query.name}`.`status`"},
            },
        ]
        context = {"chart": chart.name, "filters": {"Forged": {"operator": "=", "value": "Closed"}}}

        with as_user(DESK_USER), db_connections():
            values = forged.get_distinct_column_values("Description", filter_context=context)

        # unnarrowed: the list is the published filter's whole offer, not the
        # answer to "which of these are Closed"
        self.assertEqual(sorted(values), sorted(OWNER_TODOS))

    # @feature permissions.request-body-not-trusted
    def test_an_insights_user_cannot_claim_write_on_the_dashboard_in_hand(self):
        """The write check is about this very document, so it is asked by name.
        `has_doc_permission` reads `owner` and `__islocal` off the object it is
        handed, and both are copied straight out of the request body."""
        query, chart, dashboard = self.make_content(visibility="Everyone")
        frappe.db.set_value(DT.CHART, chart.name, "run_as_owner", 1, update_modified=False)

        forged_items = [
            *frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items")),
            {
                "id": "forged",
                "type": "filter",
                "filter_name": "Forged",
                "filter_type": "String",
                "links": {chart.name: f"`{query.name}`.`status`"},
            },
        ]
        context = {"chart": chart.name, "filters": {"Forged": {"operator": "=", "value": "Closed"}}}
        stored = frappe.get_doc(DT.DASHBOARD, dashboard.name).as_dict()

        with as_user(OUTSIDER), db_connections():
            for claim in ({"__islocal": 1}, {"owner": OUTSIDER}):
                forged = frappe.get_doc({**stored, "items": forged_items, **claim})
                values = forged.get_distinct_column_values("Description", filter_context=context)
                self.assertEqual(sorted(values), sorted(OWNER_TODOS), claim)

    # @feature permissions.chart-cannot-link-unreadable-query permissions.denied-is-not-found
    def test_a_filter_cannot_read_a_query_the_dashboard_does_not_reach(self):
        """A filter link names a query, and whoever may save the dashboard wrote
        that row. A link routes nowhere unless the card already reads the query
        it names, so one that does not is no filter at all — and a filter that is
        not on this dashboard answers like any other reference the caller may not
        have."""
        _, chart, dashboard = self.make_content(visibility="Everyone")

        with as_user(OUTSIDER):
            other_workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            unreachable = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "View API Test Unreachable Query",
                    "workbook": other_workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()

        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items"))
        items.append(
            {
                "type": "filter",
                "filter_name": "Elsewhere",
                "filter_type": "String",
                "links": {chart.name: f"`{unreachable.name}`.`description`"},
                "layout": {"i": "filter-2", "x": 0, "y": 2, "w": 4, "h": 1},
            }
        )
        frappe.db.set_value(DT.DASHBOARD, dashboard.name, "items", json.dumps(items), update_modified=False)

        with as_user(DESK_USER), db_connections(), self.assertRaises(frappe.DoesNotExistError):
            get_filter_values(dashboard=dashboard.name, filter_name="Elsewhere")

        # and the owner of both, who may read the query the link names, is
        # refused by the same rule: the card is what says where a filter lands
        with as_user(OWNER), db_connections(), self.assertRaises(frappe.DoesNotExistError):
            get_filter_values(dashboard=dashboard.name, filter_name="Elsewhere")

    # @feature permissions.chart-cannot-link-unreadable-query permissions.chart-run-as-owner
    def test_a_filter_reaches_a_query_one_step_under_the_card(self):
        """A summarized card's own query names no dimension column, so a filter
        on it links a query a hop further down — the move the editor offers, and
        the only one that works. `view.get_filter_values` answers the card's
        reader through the chart, because the number they are looking at was
        computed through that query - not through a grant on the query, which a
        level alone never gives."""
        _, chart, dashboard = self.make_content(visibility="Everyone")
        frappe.db.set_value(DT.CHART, chart.name, "run_as_owner", 1, update_modified=False)

        # a source of the card's own query: in the graph the card reads, and
        # granted to nobody the dashboard admits
        with as_user(OWNER):
            source = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "View API Test Source Query",
                    "workbook": chart.workbook,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            sourced = frappe.get_doc(DT.QUERY, chart.query)
            sourced.operations = json.dumps(
                [{"type": "source", "table": {"type": "query", "query_name": source.name}}]
            )
            sourced.save()

        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items"))
        items.append(
            {
                "type": "filter",
                "filter_name": "Underneath",
                "filter_type": "String",
                "links": {chart.name: f"`{source.name}`.`description`"},
                "layout": {"i": "filter-3", "x": 0, "y": 3, "w": 4, "h": 1},
            }
        )
        frappe.db.set_value(DT.DASHBOARD, dashboard.name, "items", json.dumps(items), update_modified=False)

        # the level published the picture, not the pipeline behind it
        with as_user(DESK_USER):
            self.assertFalse(may_read(frappe.get_doc(DT.QUERY, source.name)))

        with as_user(DESK_USER), db_connections():
            values = get_filter_values(dashboard=dashboard.name, filter_name="Underneath")

        self.assertEqual(sorted(values), sorted(OWNER_TODOS))

    # @feature permissions.chart-cannot-link-unreadable-query
    def test_one_unreadable_link_does_not_refuse_the_filter_behind_it(self):
        """`links` is a dict in the order the author toggled the cards, so a
        link this caller may not read must be skipped and not thrown on — or the
        same dashboard answers or refuses depending on which card was toggled
        first."""
        _, chart, dashboard = self.make_content(visibility="Everyone")
        elsewhere = self.make_second_chart(dashboard)
        frappe.db.set_value(DT.CHART, chart.name, "run_as_owner", 1, update_modified=False)

        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items"))
        items.append(
            {
                "type": "filter",
                "filter_name": "Either",
                "filter_type": "String",
                # the refused card first, which is what makes this reachable
                "links": {
                    elsewhere.name: f"`{elsewhere.query}`.`description`",
                    chart.name: f"`{chart.query}`.`description`",
                },
                "layout": {"i": "filter-4", "x": 0, "y": 4, "w": 4, "h": 1},
            }
        )
        frappe.db.set_value(DT.DASHBOARD, dashboard.name, "items", json.dumps(items), update_modified=False)

        self.narrow_to_query(DESK_USER, chart.query)

        with as_user(DESK_USER):
            self.assertFalse(may_read(frappe.get_doc(DT.CHART, elsewhere.name)))

        with as_user(DESK_USER), db_connections():
            values = get_filter_values(dashboard=dashboard.name, filter_name="Either")

        self.assertEqual(sorted(values), sorted(OWNER_TODOS))

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

    # more than the picture: a page past the first, the count, the file

    def paged_content(self, visibility="Everyone"):
        """A chart that runs as its owner, one row a page, over the owner's two todos."""
        _, chart, dashboard = self.make_content(visibility=visibility)
        config = table_config()
        config["limit"] = 1
        chart.db_set({"run_as_owner": 1, "config": frappe.as_json(config)}, update_modified=False)

        original = frappe.db.get_single_value(DT.SETTINGS, "allow_download")
        self.addCleanup(frappe.db.set_single_value, DT.SETTINGS, "allow_download", original)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 1)
        return chart, dashboard

    def assert_picture_only(self, user, chart, dashboard):
        first = self.fetch_data(user, chart.name, dashboard.name, force=True)
        second = self.fetch_data(user, chart.name, dashboard.name, page=2, force=True)

        self.assertEqual(len(first["rows"]), 1)
        self.assertFalse(first["can_read_rows"])
        self.assertFalse(first["can_export"])
        # a page past the first is answered with the first
        self.assertEqual(second["rows"], first["rows"])
        with as_user(user), db_connections():
            with self.assertRaises(NotPermitted):
                get_chart_count(chart=chart.name, dashboard=dashboard.name)
            with self.assertRaises(frappe.PermissionError):
                download_chart_rows(chart=chart.name, dashboard=dashboard.name)

    # @feature charts.table-pager charts.export-rows
    def test_a_reader_who_may_read_rows_pages_counts_and_downloads(self):
        """`view.get_chart_data`, `get_chart_count` and `download_chart_rows`,
        which every view surface's table card calls."""
        chart, dashboard = self.paged_content()

        first = self.fetch_data(OWNER, chart.name, dashboard.name, force=True)
        second = self.fetch_data(OWNER, chart.name, dashboard.name, page=2, force=True)
        with as_user(OWNER), db_connections():
            count = get_chart_count(chart=chart.name, dashboard=dashboard.name, force=True)
            csv = download_chart_rows(chart=chart.name, dashboard=dashboard.name)

        self.assertTrue(first["can_read_rows"])
        self.assertTrue(first["can_export"])
        self.assertEqual(sorted(self.descriptions(first) + self.descriptions(second)), sorted(OWNER_TODOS))
        self.assertEqual(count, len(OWNER_TODOS))
        # the chart's own rows, summarized as it draws them
        lines = csv.strip().splitlines()
        self.assertEqual(lines[0], "description,count")
        self.assertEqual(len(lines), 1 + len(OWNER_TODOS))

    # @feature charts.table-pager charts.export-rows permissions.chart-run-as-owner
    def test_a_reader_shown_the_picture_keeps_the_charts_one_page(self):
        """The same three endpoints, for a reader of a run-as-owner chart who may not write it."""
        chart, dashboard = self.paged_content()

        self.assert_picture_only(DESK_USER, chart, dashboard)

    # @feature charts.table-pager charts.export-rows shared.no-drill
    def test_a_guest_keeps_a_public_charts_one_page(self):
        """The same three endpoints, for a guest on a public link."""
        chart, dashboard = self.paged_content(visibility="Public")

        self.assert_picture_only(GUEST, chart, dashboard)

    # @feature shared.no-drill charts.table-pager dashboard.card-filter permissions.run-as-owner-lapses
    def test_a_guest_gets_no_more_than_the_picture_of_a_public_chart_run_as_its_reader(self):
        """`get_chart_count`, and the `can_read_rows` and `can_filter` answers
        `view.get_chart_data` sends the card, on a Public chart that runs as its
        reader: the box off, or its owner disabled. A signed-in reader of the
        same chart still reads their own rows."""
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import can_filter_card
        from insights.permissions import can_read_rows

        chart, _ = self.paged_content(visibility="Public")
        # a guest whose own rows are Not Permitted finds no dashboard of them
        # (`has_permitted_chart`); the chart's own link still reaches the chart
        chart.db_set("visibility", "Public", update_modified=False)

        def as_its_reader(box_off):
            chart.db_set("run_as_owner", int(not box_off), update_modified=False)
            if not box_off:
                frappe.db.set_value("User", OWNER, "enabled", 0)
                self.addCleanup(frappe.db.set_value, "User", OWNER, "enabled", 1)

        for box_off in (True, False):
            with self.subTest(box_off=box_off):
                as_its_reader(box_off)
                stored = frappe.get_doc(DT.CHART, chart.name)
                with as_user(GUEST), db_connections():
                    self.assertFalse(can_read_rows(stored))
                    self.assertFalse(can_filter_card(chart.name))
                    with self.assertRaisesRegex(NotPermitted, "behind this chart"):
                        get_chart_count(chart=chart.name)
                    with self.assertRaises(frappe.PermissionError):
                        download_chart_rows(chart=chart.name)
                with as_user(DESK_USER):
                    self.assertTrue(can_read_rows(stored))
