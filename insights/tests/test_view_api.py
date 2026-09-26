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
# has no Insights role and reads content through its visibility level
DESK_USER = "view_api_desk_user@test.com"
# has an Insights role, but no access to the owner's content
OUTSIDER = "view_api_outsider@test.com"
# owns nothing. A shipped workbook belongs to whoever ran migrate, so a site's
# admin copies content they do not own
ADMIN = "view_api_admin@test.com"
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
    """A configured chart: one row per description, counted. The chart's rows
    depend on this config alone; nothing else describes its query."""
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
        create_user(ADMIN, first_name="View", last_name="Admin", roles=["Insights User", "System Manager"])

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
        delete_users(OWNER, OUTSIDER, DESK_USER, ADMIN)

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
                    # the chart is Private, so only the dashboard's
                    # visibility can give access to it
                    "visibility": "Private",
                    # a Public dashboard includes only charts that run as their owner
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
        """Mark the content shipped, as an import does."""
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
        """A dashboard's visibility level reaches every chart on it, but a User
        Permission still limits the reader. One on the first chart's query
        refuses the second chart. Sending its title or config would count as
        reading it."""
        _, chart, dashboard = self.make_content(visibility="Everyone")
        elsewhere = self.make_second_chart(dashboard)
        self.narrow_to_query(DESK_USER, chart.query)

        with as_user(DESK_USER):
            response = get_dashboard(dashboard=dashboard.name)
            # `get_chart` refuses the same chart
            with self.assertRaises(frappe.DoesNotExistError):
                get_chart(chart=elsewhere.name, dashboard=dashboard.name)

        self.assertEqual([shown["name"] for shown in response["charts"]], [chart.name])
        # the cell goes too. A cell that names a chart missing from `charts`
        # shows "Chart not found". The docname of refused content also leaks it:
        # after a workbook is shipped, the docname is the title in readable form
        named = [item.get("chart") for item in response["items"] if item["type"] == "chart"]
        self.assertEqual(named, [chart.name])
        self.assertNotIn(elsewhere.name, frappe.as_json(response))

    # @feature permissions.denied-is-not-found
    def test_a_dashboard_with_no_chart_this_reader_may_read_is_not_found(self):
        """Not Found is the only answer for content a reader may not read. A grid
        of "Chart not found" cards is not an answer."""
        _, chart, dashboard = self.make_content(visibility="Everyone")
        elsewhere = self.make_second_chart(dashboard)

        # the grid keeps one chart, whose query the reader's User Permission
        # excludes
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
        """A chart that no longer exists was not refused to the reader. Before a
        chart's delete removed its cells, the delete left a cell that named
        it."""
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
        # delete the chart but keep its cell, as older deletes did
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
        # the desk user sees the owner's rows, because the chart runs as its owner
        chart.db_set("run_as_owner", 1, update_modified=False)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))
        self.assertIn("description", [column["name"] for column in result["columns"]])

    # @feature permissions.chart-run-as-owner
    def test_chart_data_stays_under_the_declared_permissions(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        self.assertFalse(chart.run_as_owner)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        # with Run as owner off, the engine applies the reader's own permissions,
        # so a roleless reader sees none of the owner's rows
        self.assertEqual(self.descriptions(result), [])

    # @feature charts.missing-slot-message
    def test_an_unconfigured_chart_says_so_instead_of_showing_its_source(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("run_as_owner", 1, update_modified=False)
        # a table chart with no rows configured. Falling back to the source query
        # here used to show the raw table as the chart
        chart.db_set("config", frappe.as_json({"limit": 50}), update_modified=False)

        result = self.fetch_data(DESK_USER, chart.name, dashboard.name, force=True)

        # the builder's message for what is missing, and no rows
        self.assertEqual(result["errors"], ["Rows are required"])
        self.assertNotIn("rows", result)

    # @feature charts.table-rows-columns-values
    def test_chart_data_follows_the_config_with_nothing_to_refresh(self):
        _, chart, dashboard = self.make_content(visibility="Everyone")
        chart.db_set("run_as_owner", 1, update_modified=False)

        self.assertEqual(
            self.descriptions(self.fetch_data(DESK_USER, chart.name, dashboard.name)), sorted(OWNER_TODOS)
        )

        # the config fully describes the query, so editing it is enough. There is
        # no builder session or second document to keep in sync
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
            # the grant is on the document, not on the path to it, so the chart
            # also resolves without a dashboard
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

        # saved, not db_set: the save refuses a Public dashboard with a chart that
        # runs as its reader, because a guest has no permissions and would see an
        # empty page
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
        """A dashboard opened anywhere counts toward what the reader viewed last.

        A guest is counted too. All guests are one user, so their rows are a
        lower bound on public views. `site_profile` reads them that way.
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

        # shipped content is editable only on a developer-mode bench; this is
        # the answer for every other site
        with patch.dict(frappe.conf, {"developer_mode": 0}):
            with as_user(OWNER):
                response = get_dashboard(dashboard=dashboard.name)
            # the owner holds write rights, but shipped content is read-only here
            self.assertFalse(response["can_write"])
            self.assertTrue(response["can_copy"])

            # copying is an authoring action, so a roleless reader cannot copy
            with as_user(DESK_USER):
                response = get_dashboard(dashboard=dashboard.name)
            self.assertFalse(response["can_copy"])
            self.assertIsNone(response["workbook"])

    # @feature standard.duplicate
    def test_shipped_content_does_not_allow_copying_without_workbook_read(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        dashboard = self.ship(dashboard)

        with patch.dict(frappe.conf, {"developer_mode": 0}), as_user(OUTSIDER):
            self.assertFalse(frappe.has_permission(DT.WORKBOOK, "read", dashboard.workbook))
            response = get_dashboard(dashboard=dashboard.name)
            self.assertFalse(response["can_copy"])
            self.assertIsNone(response["workbook"])

    # @feature standard.duplicate
    def test_a_shipped_workbook_allows_copying_and_the_copy_is_the_sites(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        dashboard = self.ship(dashboard)

        with patch.dict(frappe.conf, {"developer_mode": 0}), as_user(ADMIN):
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
    def test_no_response_includes_the_query_behind_the_chart(self):
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
        """The answer includes the `chart` with its rows, and `makeSavedChartView`
        loads both in one step. So a card never holds a definition that its rows
        do not match. The chart is edited between two unforced reads, as an
        author in another tab would."""
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
        # a drill from this card sends this version back
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
        # enough to refetch only those cards and to let an empty card name the
        # filter, without exposing the column it filters
        self.assertEqual(filter_item["charts"], [chart.name])
        self.assertEqual(filter_item["filter_type"], "String")

    # @feature dashboard.filter-user-default
    def test_a_filter_default_is_each_readers_own_user_default(self):
        _, _, dashboard = self.make_content(visibility="Everyone")
        items = frappe.parse_json(dashboard.items)
        items[1].update(default_operator="=", default_value="Fixed", default_user_key="Company")
        dashboard.db_set("items", frappe.as_json(items), update_modified=False)
        # ERPNext stores the default company under the scrubbed key
        frappe.defaults.set_user_default("company", "Desk Co", DESK_USER)
        frappe.defaults.set_user_default("company", "Admin Co", ADMIN)

        def default_value(user):
            with as_user(user):
                response = get_dashboard(dashboard=dashboard.name)
            return next(item for item in response["items"] if item["type"] == "filter")["default_value"]

        self.assertEqual(default_value(DESK_USER), "Desk Co")
        self.assertEqual(default_value(ADMIN), "Admin Co")

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
        """The `Insights User` check is on the endpoint, not on the computation.

        A view needs two answers that authoring clients also ask for: how many
        rows are behind a number, and which values a column has. The view's
        reader has no Insights role.
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
        # reader gets only the values their own permissions allow
        self.assertEqual(values, [])

    # @feature permissions.request-body-not-trusted
    def test_a_reader_cannot_supply_the_routing_table(self):
        """`run_doc_method` builds the document from the request body, so the
        caller controls its items. A forged link would filter a published
        filter's values by a column the author never published."""
        query, chart, dashboard = self.make_content(visibility="Everyone")
        # the chart runs as its owner, so the reader has values to filter
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

        # not filtered: the list holds all of the published filter's values, not
        # only the Closed ones
        self.assertEqual(sorted(values), sorted(OWNER_TODOS))

    # @feature permissions.request-body-not-trusted
    def test_an_insights_user_cannot_claim_write_on_the_dashboard_in_hand(self):
        """The write check must be about the stored document, so it looks the
        document up by name. `has_doc_permission` reads `owner` and `__islocal`
        from the object it gets, and both come from the request body."""
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
        """A filter link names a query, and anyone who may save the dashboard can
        write it. A link applies only if the card already reads the query it
        names. Otherwise the filter is Not Found, like any other reference the
        caller may not read."""
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

        # the owner of both can read the linked query, and is refused by the
        # same rule: the card decides where a filter applies
        with as_user(OWNER), db_connections(), self.assertRaises(frappe.DoesNotExistError):
            get_filter_values(dashboard=dashboard.name, filter_name="Elsewhere")

    # @feature permissions.chart-cannot-link-unreadable-query permissions.chart-run-as-owner
    def test_a_filter_reaches_a_query_one_step_under_the_card(self):
        """A summarized card's own query has no dimension column, so a filter on
        it links a query one step further down. The editor lists that query, and
        it is the only link that works. `view.get_filter_values` answers through
        the chart, because the reader's number was computed through that query.
        A visibility level never grants read on the query itself."""
        _, chart, dashboard = self.make_content(visibility="Everyone")
        frappe.db.set_value(DT.CHART, chart.name, "run_as_owner", 1, update_modified=False)

        # a source of the card's query: part of what the card reads, but granted
        # to no reader of the dashboard
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

        # the visibility level shares the chart, not the queries behind it
        with as_user(DESK_USER):
            self.assertFalse(may_read(frappe.get_doc(DT.QUERY, source.name)))

        with as_user(DESK_USER), db_connections():
            values = get_filter_values(dashboard=dashboard.name, filter_name="Underneath")

        self.assertEqual(sorted(values), sorted(OWNER_TODOS))

    # @feature permissions.chart-cannot-link-unreadable-query
    def test_one_unreadable_link_does_not_refuse_the_filter_behind_it(self):
        """`links` keeps the order in which the author toggled the cards. A link
        the caller may not read must be skipped, not raised. Otherwise the same
        dashboard answers or refuses depending on which card was toggled
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
                # the refused card first, so the skip is tested
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

    # beyond the chart: later pages, the row count, the download

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

    def assert_chart_only(self, user, chart, dashboard):
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
        """Every view's table card calls `view.get_chart_data`, `get_chart_count`
        and `download_chart_rows`."""
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
        # the chart's own rows, summarized as it shows them
        lines = csv.strip().splitlines()
        self.assertEqual(lines[0], "description,count")
        self.assertEqual(len(lines), 1 + len(OWNER_TODOS))

    # @feature charts.table-pager charts.export-rows permissions.chart-run-as-owner
    def test_a_reader_of_a_run_as_owner_chart_keeps_its_one_page(self):
        """The same three endpoints, for a reader of a run-as-owner chart who may not write it."""
        chart, dashboard = self.paged_content()

        self.assert_chart_only(DESK_USER, chart, dashboard)

    # @feature charts.table-pager charts.export-rows shared.no-drill
    def test_a_guest_keeps_a_public_charts_one_page(self):
        """The same three endpoints, for a guest on a public link."""
        chart, dashboard = self.paged_content(visibility="Public")

        self.assert_chart_only(GUEST, chart, dashboard)

    # @feature shared.no-drill charts.table-pager dashboard.card-filter permissions.run-as-owner-lapses
    def test_a_guest_of_a_public_chart_run_as_its_reader_gets_only_the_chart(self):
        """A Public chart runs as its reader when Run as owner is off or its
        owner is disabled. A guest then gets no row count, and no `can_read_rows`
        or `can_filter` from `view.get_chart_data`. A signed-in reader of the
        same chart still reads their own rows."""
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import can_filter_card
        from insights.permissions import can_read_rows

        chart, _ = self.paged_content(visibility="Public")
        # the dashboard is Not Found for a guest with no permitted chart
        # (`has_permitted_chart`), but the chart's own link still reaches it
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
