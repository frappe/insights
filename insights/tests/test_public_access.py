"""A link names what its author can read.

A chart's `query` and a dashboard's `linked_charts` are grants: the permission
queries in `insights.permissions` read a link as access. So a link is checked
where it is written, not where it is followed.
"""

import frappe

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
        """Public in a single insert, so the check runs before the level lands."""
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Public Chart In Other Workbook",
                    "workbook": self.other_workbook,
                    "query": self.owner_query,
                    "chart_type": "Bar",
                    "visibility": "Public",
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

    # @feature permissions.dashboard-cannot-hold-unreadable-chart
    def test_a_dashboard_cannot_hold_a_chart_of_another_workbook(self):
        """`frappe.client.save` from the dashboard builder. Reading the chart is
        not enough: a dashboard's filters narrow the charts on it, and only the
        chart's own workbook writes those."""
        frappe.db.set_value(DT.CHART, self.owner_chart, "visibility", "Everyone")
        self.addCleanup(frappe.db.set_value, DT.CHART, self.owner_chart, "visibility", "Private")

        with self.as_user(OTHER):
            self.assertTrue(frappe.has_permission(DT.CHART, ptype="read", doc=self.owner_chart))
            with self.assertRaises(frappe.ValidationError):
                frappe.get_doc(
                    {
                        "doctype": DT.DASHBOARD,
                        "title": "Dashboard In Other Workbook",
                        "workbook": self.other_workbook,
                        "items": [{"id": "chart-1", "type": "chart", "chart": self.owner_chart}],
                    }
                ).insert()

    # @feature shared.chart-link
    def test_publishing_your_own_chart_still_works(self):
        """The query is readable, so the check the rules above make does not fire."""
        with self.as_user(OWNER):
            chart = frappe.get_doc(DT.CHART, self.owner_chart)
            chart.visibility = "Public"
            chart.save()

        self.assertEqual(frappe.db.get_value(DT.CHART, self.owner_chart, "visibility"), "Public")

    # @feature shared.dashboard-link
    def test_publishing_your_own_dashboard_still_works(self):
        """The chart is readable, so the check the rules above make does not fire."""
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

            chart = frappe.get_doc(DT.CHART, self.owner_chart)
            chart.run_as_owner = 1
            chart.save()
            dashboard.visibility = "Public"
            dashboard.save()

        self.assertEqual(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "visibility"), "Public")


class TestCardFilterRouting(InsightsIntegrationTestCase):
    """A card filter is the reader's, so it reaches only what the card draws."""

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title="Routing Workbook").name
        cls.query = create_test_query(OWNER, cls.workbook, title="Routing Query").name
        cls.chart = create_test_chart(OWNER, cls.workbook, query=cls.query, title="Routing Chart").name
        cls.dashboard = create_test_dashboard(OWNER, cls.workbook, chart=cls.chart, title="Routing Dashboard")
        with as_user(OWNER):
            chart = frappe.get_doc(DT.CHART, cls.chart)
            chart.run_as_owner = 1
            chart.save()
            cls.dashboard.items = [
                {"id": "chart-1", "type": "chart", "chart": cls.chart},
                {
                    "id": "filter-1",
                    "type": "filter",
                    "filter_name": "Region",
                    "links": {cls.chart: f"`{cls.query}`.`region`"},
                },
            ]
            cls.dashboard.visibility = "Public"
            cls.dashboard.save()

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    # @feature dashboard.card-filter
    def test_a_card_filter_lands_on_the_card_s_own_query(self):
        """It names a column the card draws, so it reaches no other query.
        `InsightsChartv3.fetch` routes it; the chart runs as its owner, and only
        the owner may filter it."""
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            route_card_filters,
        )

        with as_user(OWNER):
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
        with as_user(OWNER):
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
        from insights.api.view import get_card_values

        with self.assertRaises(frappe.DoesNotExistError):
            get_card_values(self.chart, "a_column_nobody_drew", self.dashboard.name)

    # @feature shared.filters-on-public-dashboard
    def test_a_reader_cannot_ask_about_a_chart_this_grid_does_not_hold(self):
        other = create_test_chart(OWNER, self.workbook, query=self.query, title="Off Grid").name
        from insights.api.view import get_card_values

        with self.assertRaises(frappe.DoesNotExistError):
            get_card_values(other, "region", self.dashboard.name)
