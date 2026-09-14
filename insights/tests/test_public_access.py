"""A link names what its author can read, and a public document runs as published.

Two rules over the same boundary. A chart's `query` and a dashboard's
`linked_charts` are grants: the permission queries in `insights.permissions` read
a link as access, and `insights.api.shared` reads a link from a public document
the same way. So a link is checked where it is written.

Once a document is public, the arguments its methods accept come from the
request. `insights.api.PUBLIC_METHOD_ARGS` names them, so the query builder's own
parameters stay with the builder.

Name lookup follows the same boundary: an old name resolves to the document it
now names only for a caller who can read it, or for one that is published.
"""

import frappe

from insights.api.shared import get_chart_name, get_dashboard_name
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import USER_1, USER_2, create_test_users

OWNER = USER_1
OTHER = USER_2


class TestLinkRequiresReadAccess(InsightsIntegrationTestCase):
    """A chart's query and a dashboard's charts are grants, so both are checked."""

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.owner_workbook = create_test_workbook(OWNER, title="Owner Workbook").name
        cls.owner_query = create_test_query(OWNER, cls.owner_workbook, title="Owner Query").name
        cls.owner_chart = create_test_chart(
            OWNER, cls.owner_workbook, query=cls.owner_query, title="Owner Chart"
        ).name
        cls.other_workbook = create_test_workbook(OTHER, title="Other Workbook").name

    @classmethod
    def after_class(cls):
        for doctype, name in (
            (DT.WORKBOOK, cls.owner_workbook),
            (DT.WORKBOOK, cls.other_workbook),
        ):
            frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    # @feature permissions.chart-cannot-link-unreadable-query
    def test_a_query_in_another_workbook_is_not_readable(self):
        """The baseline the rules below are measured against."""
        with self.as_user(OTHER):
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=self.owner_query))

    # @feature permissions.chart-cannot-link-unreadable-query
    def test_a_chart_cannot_link_an_unreadable_query(self):
        """A chart the caller owns makes its query readable, so the check cannot
        wait for the chart to be published."""
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Chart In Other Workbook",
                    "workbook": self.other_workbook,
                    "query": self.owner_query,
                    "chart_type": "Bar",
                    "config": {},
                }
            ).insert()

    # @feature permissions.chart-cannot-link-unreadable-query
    def test_a_public_chart_cannot_link_an_unreadable_query(self):
        """Public in a single insert, so the check runs before the flag lands."""
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Public Chart In Other Workbook",
                    "workbook": self.other_workbook,
                    "query": self.owner_query,
                    "chart_type": "Bar",
                    "is_public": 1,
                    "config": {},
                }
            ).insert()

    # @feature permissions.chart-cannot-link-unreadable-query
    def test_an_existing_chart_cannot_be_repointed(self):
        """A link written on update is checked the same as one written on insert."""
        with self.as_user(OTHER):
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Repointed Chart",
                    "workbook": self.other_workbook,
                    "chart_type": "Bar",
                    "config": {},
                }
            ).insert()
            chart.query = self.owner_query
            with self.assertRaises(frappe.PermissionError):
                chart.save()

    # @feature permissions.dashboard-cannot-hold-unreadable-chart
    def test_a_dashboard_cannot_hold_an_unreadable_chart(self):
        """A chart on a dashboard the caller can read is readable, so naming one
        here is the same grant one level up.

        Written through `items`, which is what the client sends. `linked_charts`
        is derived from it, so a check that reads the stored rows would see the
        state before this save.
        """
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Dashboard In Other Workbook",
                    "workbook": self.other_workbook,
                    "items": [{"id": "chart-1", "type": "chart", "chart": self.owner_chart}],
                }
            ).insert()

    # @feature permissions.dashboard-cannot-hold-unreadable-chart
    def test_a_dashboard_cannot_take_on_an_unreadable_chart(self):
        """The same on update: an existing dashboard gains an item."""
        with self.as_user(OTHER):
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Growing Dashboard",
                    "workbook": self.other_workbook,
                    "items": [],
                }
            ).insert()
            dashboard.items = [{"id": "chart-1", "type": "chart", "chart": self.owner_chart}]
            with self.assertRaises(frappe.PermissionError):
                dashboard.save()

    # @feature shared.chart-link
    def test_publishing_your_own_chart_still_works(self):
        with self.as_user(OWNER):
            chart = frappe.get_doc(DT.CHART, self.owner_chart)
            chart.update_access(is_public=True)
            self.assertTrue(frappe.db.get_value(DT.CHART, chart.name, "is_public"))

    # @feature shared.dashboard-link
    def test_publishing_your_own_dashboard_still_works(self):
        with self.as_user(OWNER):
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Legitimate Dashboard",
                    "workbook": self.owner_workbook,
                    "items": [{"id": "chart-1", "type": "chart", "chart": self.owner_chart}],
                }
            ).insert()
            self.assertEqual([row.chart for row in dashboard.linked_charts], [self.owner_chart])
            dashboard.update_access(
                {"is_public": 1, "is_shared_with_organization": 0, "people_with_access": []}
            )
            self.assertTrue(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "is_public"))


class TestPublicMethodArguments(InsightsIntegrationTestCase):
    """The builder's own parameters are not part of the public contract."""

    def filter_args(self, doctype, method, args):
        from insights.api import public_method_args

        return public_method_args(doctype, method, args)

    # @feature shared.public-methods-bounded
    def test_a_builder_parameter_is_dropped(self):
        """A forced re-run bypasses the cache, so it stays with the builder."""
        args = self.filter_args(DT.CHART, "get_data", {"force": True, "page_size": 100})
        self.assertNotIn("force", args)
        self.assertEqual(args, {"page_size": 100})

    # @feature shared.public-methods-bounded
    def test_a_json_string_body_is_filtered_too(self):
        """`args` arrives as a JSON body, so filtering must survive the parse."""
        args = self.filter_args(DT.CHART, "get_data", '{"force": true, "page": 2}')
        self.assertEqual(args, {"page": 2})

    # @feature shared.public-methods-bounded
    def test_a_download_is_not_a_public_method(self):
        """No reading surface downloads: the export button belongs to the builder."""
        from insights.api import is_public_method

        self.assertFalse(is_public_method(DT.QUERY, "download_results"))

    # @feature shared.public-methods-bounded
    def test_no_public_method_accepts_a_builder_parameter(self):
        """The rule, not one parameter name."""
        from insights.api import PUBLIC_METHOD_ARGS

        builder_only = {"active_operation_idx", "force", "use_live_connection", "limit"}
        for (doctype, method), allowed in PUBLIC_METHOD_ARGS.items():
            self.assertFalse(
                allowed & builder_only,
                f"{doctype}.{method} exposes {allowed & builder_only} to Guests",
            )

    # @feature shared.public-methods-bounded
    def test_every_public_method_declares_its_arguments(self):
        """is_public_method and the argument surface are one map, so they cannot drift."""
        from insights.api import PUBLIC_METHOD_ARGS, is_public_method

        for doctype, method in PUBLIC_METHOD_ARGS:
            self.assertTrue(is_public_method(doctype, method))

    # @feature shared.public-methods-bounded
    def test_a_public_read_sends_no_routing_table(self):
        """A filter link names a query and a column, so a routing table from the
        request is a reader naming columns nobody published."""
        args = self.filter_args(
            DT.CHART,
            "get_data",
            {"dashboard_items": [{"type": "filter"}], "filters": {}, "card_filters": []},
        )
        self.assertEqual(args, {"filters": {}, "card_filters": []})

    # @feature shared.public-methods-bounded
    def test_the_card_value_path_keeps_what_it_needs(self):
        """A card filter names a column the card draws, on a chart the grid holds."""
        args = self.filter_args(
            DT.DASHBOARD,
            "get_card_column_values",
            {"chart": "c1", "column": "region", "search_term": "no", "query": "q1"},
        )
        self.assertEqual(args, {"chart": "c1", "column": "region", "search_term": "no"})

    # @feature shared.public-methods-bounded
    def test_the_dashboard_filter_path_keeps_what_it_needs(self):
        """The filter names itself. The column behind it is read off the dashboard."""
        context = {"chart": "c1", "items": [], "filters": {}}
        args = self.filter_args(
            DT.DASHBOARD,
            "get_distinct_column_values",
            {"filter_name": "Status", "search_term": "op", "filter_context": context, "query": "q1"},
        )
        self.assertEqual(args, {"filter_name": "Status", "search_term": "op", "filter_context": context})


class TestPublicFilterRouting(InsightsIntegrationTestCase):
    """A public read routes through the dashboard that published the chart."""

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title="Routing Workbook").name
        cls.query = create_test_query(OWNER, cls.workbook, title="Routing Query").name
        cls.chart = create_test_chart(OWNER, cls.workbook, query=cls.query, title="Routing Chart").name
        cls.dashboard = create_test_dashboard(OWNER, cls.workbook, chart=cls.chart, title="Routing Dashboard")
        with as_user(OWNER):
            cls.dashboard.items = [
                {"id": "chart-1", "type": "chart", "chart": cls.chart},
                {
                    "id": "filter-1",
                    "type": "filter",
                    "filter_name": "Region",
                    "links": {cls.chart: f"`{cls.query}`.`region`"},
                },
            ]
            cls.dashboard.save()
            cls.dashboard.update_access(
                {"is_public": 1, "is_shared_with_organization": 0, "people_with_access": []}
            )

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    # @feature shared.filters-on-public-dashboard
    def test_the_routing_table_is_the_published_dashboard_s(self):
        from insights.api.shared import published_dashboard_items

        items = published_dashboard_items(self.chart)
        self.assertEqual(
            [item.get("filter_name") for item in items if item.get("type") == "filter"],
            ["Region"],
        )

    # @feature shared.filters-on-public-dashboard
    def test_a_chart_published_on_no_dashboard_routes_nothing(self):
        from insights.api.shared import published_dashboard_items

        with as_user(OWNER):
            lone = create_test_chart(OWNER, self.workbook, query=self.query, title="Lone Chart")
            frappe.db.set_value(DT.CHART, lone.name, "is_public", 1)

        self.assertIsNone(published_dashboard_items(lone.name))

    # @feature dashboard.card-filter
    def test_a_card_filter_lands_on_the_card_s_own_query(self):
        """It names a column the card draws, so it reaches no other query."""
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            route_card_filters,
        )

        routed = route_card_filters(
            self.chart, [{"column": "region", "operator": "=", "value": "North"}], None
        )
        self.assertEqual(list(routed), [self.chart])
        self.assertEqual(
            routed[self.chart]["filters"],
            [
                {
                    "type": "filter",
                    "column": {"type": "column", "column_name": "region"},
                    "operator": "=",
                    "value": "North",
                }
            ],
        )

    # @feature dashboard.card-filter
    def test_a_card_filter_joins_the_routed_ones(self):
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            route_card_filters,
        )

        existing = {self.query: {"type": "filter_group", "logical_operator": "And", "filters": [{}]}}
        routed = route_card_filters(
            self.chart, [{"column": "region", "operator": "=", "value": "North"}], existing
        )
        self.assertEqual(set(routed), {self.query, self.chart})

    # @feature dashboard.card-filter
    def test_a_card_filter_that_names_no_column_is_dropped(self):
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            route_card_filters,
        )

        self.assertIsNone(route_card_filters(self.chart, [{"operator": "="}], None))

    # @feature shared.filters-on-public-dashboard
    def test_a_reader_cannot_ask_for_a_column_the_card_does_not_draw(self):
        with self.assertRaises(frappe.PermissionError):
            self.dashboard.get_card_column_values(self.chart, "a_column_nobody_drew")

    # @feature shared.filters-on-public-dashboard
    def test_a_reader_cannot_ask_about_a_chart_this_grid_does_not_hold(self):
        other = create_test_chart(OWNER, self.workbook, query=self.query, title="Off Grid").name
        with self.assertRaises(frappe.PermissionError):
            self.dashboard.get_card_column_values(other, "region")


class TestRenamedNameLookup(InsightsIntegrationTestCase):
    """A v2 link carries the old name, and a Guest following one has to resolve it."""

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title="Renamed Workbook").name
        cls.query = create_test_query(OWNER, cls.workbook, title="Renamed Query").name
        cls.chart = create_test_chart(OWNER, cls.workbook, query=cls.query, title="Renamed Chart").name
        cls.published = create_test_dashboard(
            OWNER, cls.workbook, chart=cls.chart, title="Published Dashboard"
        ).name
        cls.private = create_test_dashboard(OWNER, cls.workbook, title="Private Dashboard").name

        frappe.db.set_value(DT.DASHBOARD, cls.published, "old_name", "old-published", update_modified=False)
        frappe.db.set_value(DT.DASHBOARD, cls.private, "old_name", "old-private", update_modified=False)
        frappe.db.set_value(DT.CHART, cls.chart, "old_name", "old-chart", update_modified=False)

        with as_user(OWNER):
            frappe.get_doc(DT.DASHBOARD, cls.published).update_access(
                {"is_public": 1, "is_shared_with_organization": 0, "people_with_access": []}
            )

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    # @feature shared.old-name-resolves
    def test_a_guest_resolves_the_old_name_of_a_published_dashboard(self):
        with self.as_user("Guest"):
            self.assertEqual(get_dashboard_name("old-published"), self.published)

    # @feature shared.old-name-resolves
    def test_a_guest_gets_back_the_name_it_asked_with_for_a_private_dashboard(self):
        with self.as_user("Guest"):
            self.assertEqual(get_dashboard_name("old-private"), "old-private")

    # @feature shared.chart-on-public-dashboard
    def test_a_chart_is_resolved_by_the_dashboard_that_published_it(self):
        with self.as_user("Guest"):
            self.assertEqual(get_chart_name("old-chart"), self.chart)


class TestSharedDashboardRouting(InsightsIntegrationTestCase):
    """A share link names the dashboard it opens, and that is what routes its filters."""

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title="Shared Routing Workbook").name
        cls.query = create_test_query(OWNER, cls.workbook, title="Shared Routing Query").name
        cls.chart = create_test_chart(OWNER, cls.workbook, query=cls.query, title="Shared Routing Chart").name
        cls.dashboard = create_test_dashboard(
            OWNER, cls.workbook, chart=cls.chart, title="Shared Routing Dashboard"
        )
        with as_user(OWNER):
            cls.dashboard.items = [
                {"id": "chart-1", "type": "chart", "chart": cls.chart},
                {
                    "id": "filter-1",
                    "type": "filter",
                    "filter_name": "Region",
                    "links": {cls.chart: f"`{cls.query}`.`region`"},
                },
            ]
            cls.dashboard.save()
            cls.dashboard.update_access(
                {"is_public": 0, "is_shared_with_organization": 1, "people_with_access": []}
            )

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    # @feature shared.filters-on-public-dashboard
    def test_a_reader_the_dashboard_was_shared_with_routes_through_its_links(self):
        from insights.api.shared import stored_dashboard_items

        with as_user(OTHER):
            items = stored_dashboard_items(self.chart, self.dashboard.name)

        self.assertEqual(
            [item.get("filter_name") for item in items if item.get("type") == "filter"],
            ["Region"],
        )

    # @feature shared.filters-on-public-dashboard
    def test_a_dashboard_the_reader_cannot_read_routes_nothing(self):
        from insights.api.shared import stored_dashboard_items

        with self.as_user("Guest"):
            self.assertIsNone(stored_dashboard_items(self.chart, self.dashboard.name))

    # @feature shared.filters-on-public-dashboard
    def test_a_dashboard_that_does_not_hold_the_card_routes_nothing(self):
        from insights.api.shared import stored_dashboard_items

        other = create_test_chart(OWNER, self.workbook, query=self.query, title="Off Grid Card").name
        with as_user(OTHER):
            self.assertIsNone(stored_dashboard_items(other, self.dashboard.name))
