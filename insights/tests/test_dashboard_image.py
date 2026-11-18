"""A dashboard drawn as an image for whoever asks.

The browser that draws it arrives as Guest with a preview key cut for the
caller. So the image must hold the rows the caller would see and nothing more,
under the filters they sent. The browser itself is the boundary these tests
stub: in its place, the stub reads the page's endpoints the way the page does.
"""

import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.handler import execute_cmd
from werkzeug.test import EnvironBuilder

from insights.api.view import get_chart_data, get_dashboard, get_dashboard_image
from insights.api.workbooks import update_share_permissions
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks
from insights.tests.test_view_api import table_config

OWNER = "dashboard_image_owner@test.com"
READER = "dashboard_image_reader@test.com"
OUTSIDER = "dashboard_image_outsider@test.com"

WORKBOOK_TITLE = "Dashboard Image Test Workbook"
TODO_PREFIX = "Dashboard Image Test"
OWNER_TODOS = [f"{TODO_PREFIX} owner 1", f"{TODO_PREFIX} owner 2"]
READER_TODOS = [f"{TODO_PREFIX} reader 1"]


def todo_operations():
    """ToDo's permission query limits a user without System Manager to their own
    assignments, so the owner and the reader see different rows."""
    return [
        {"type": "source", "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"}},
        {
            "type": "filter",
            "column": {"type": "column", "column_name": "description"},
            "operator": "contains",
            "value": TODO_PREFIX,
        },
    ]


def whole_page_capture(browser):
    """Frappe's capture as it takes the arguments a whole-page capture needs,
    with `browser` drawing the page."""

    def get_preview_from_url(
        url,
        wait_for=0,
        headers=None,
        format="jpg",
        width=1280,
        height=720,
        full_page=False,
        wait_until=None,
        timeout=30,
    ):
        return browser(url, headers=headers, full_page=full_page, wait_until=wait_until)

    return get_preview_from_url


class TestDashboardImage(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.cleanup()
        for user in (OWNER, READER, OUTSIDER):
            create_user(user, first_name="Image", last_name=user.split("_")[2], roles="Insights User")
        for user, descriptions in ((OWNER, OWNER_TODOS), (READER, READER_TODOS)):
            for description in descriptions:
                frappe.get_doc({"doctype": "ToDo", "description": description, "allocated_to": user}).insert(
                    ignore_permissions=True
                )

        with as_user(OWNER):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            charts = []
            for title in ("Image Chart", "Image Second Chart"):
                query = frappe.get_doc(
                    {
                        "doctype": DT.QUERY,
                        "title": f"{title} Query",
                        "workbook": workbook.name,
                        "use_live_connection": 1,
                        "is_builder_query": 1,
                        "operations": todo_operations(),
                    }
                ).insert()
                chart = frappe.get_doc(
                    {
                        "doctype": DT.CHART,
                        "title": title,
                        "workbook": workbook.name,
                        "query": query.name,
                        "chart_type": "Table",
                        "config": table_config(),
                    }
                ).insert()
                charts.append((query.name, chart.name))
            (cls.query, cls.chart), (cls.second_query, cls.second_chart) = charts
            cls.dashboard = (
                frappe.get_doc(
                    {
                        "doctype": DT.DASHBOARD,
                        "title": "Dashboard Image Test",
                        "workbook": workbook.name,
                        "items": [
                            {
                                "type": "chart",
                                "chart": chart,
                                "layout": {"i": chart, "x": 0, "y": 0, "w": 10, "h": 8},
                            }
                            for _, chart in charts
                        ]
                        + [
                            {
                                "type": "filter",
                                "filter_name": "Description",
                                "filter_type": "String",
                                "links": {chart: f"`{query}`.`description`" for query, chart in charts},
                                "layout": {"i": "filter", "x": 0, "y": 0, "w": 4, "h": 1},
                            }
                        ],
                    }
                )
                .insert()
                .name
            )
            update_share_permissions(workbook.name, [{"user": READER, "read": 1, "write": 0}])

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
        delete_users(OWNER, READER, OUTSIDER)

    def draw(self, user, **kwargs):
        """Ask for the image as `user`, and return what the browser drew: each
        card's title and rows, read as the page reads them."""
        calls = []

        def browser(url, **capture):
            calls.append(capture)
            query = parse_qs(urlparse(url).query)
            filters = json.loads(query["filters"][0]) if "filters" in query else None
            return json.dumps(self.as_browser(capture["headers"]["X-Insights-Preview-Key"], filters)).encode()

        with (
            as_user(user),
            patch("frappe.utils.preview.get_preview_from_url", whole_page_capture(browser)),
            patch("insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.check_page_answers"),
        ):
            get_dashboard_image(self.dashboard, **kwargs)
            image = json.loads(frappe.response.filecontent)
        self.assertEqual(frappe.response.filename, f"{self.dashboard}.jpg")
        self.assertTrue(calls[0]["full_page"])
        self.assertTrue(calls[0]["wait_until"])
        return image

    def as_browser(self, key, filters):
        request_was = getattr(frappe.local, "request", None)
        user_was = frappe.session.user
        frappe.local.request = EnvironBuilder(headers={"X-Insights-Preview-Key": key}).get_request()
        frappe.set_user("Guest")
        try:
            dashboard = get_dashboard(self.dashboard)
            with db_connections():
                return {
                    chart["title"]: sorted(
                        row["description"]
                        for row in get_chart_data(chart["name"], self.dashboard, filters=filters)["rows"]
                    )
                    for chart in dashboard["charts"]
                }
        finally:
            frappe.set_user(user_was)
            frappe.local.request = request_was

    def narrow_to_query(self, user, query):
        permission = frappe.get_doc(
            {"doctype": "User Permission", "user": user, "allow": DT.QUERY, "for_value": query}
        ).insert(ignore_permissions=True)
        self.addCleanup(frappe.cache.hdel, "user_permissions", user)
        self.addCleanup(
            frappe.delete_doc, "User Permission", permission.name, force=True, ignore_permissions=True
        )

    # @feature dashboard.image
    def test_each_caller_gets_an_image_of_the_rows_they_see(self):
        self.assertEqual(self.draw(OWNER)["Image Chart"], OWNER_TODOS)
        self.assertEqual(self.draw(READER)["Image Chart"], READER_TODOS)

    # @feature dashboard.image
    def test_the_image_is_drawn_under_the_callers_filters(self):
        image = self.draw(OWNER, filters={"Description": {"operator": "contains", "value": "owner 2"}})
        self.assertEqual(image["Image Chart"], [OWNER_TODOS[1]])

    # @feature dashboard.image
    def test_a_chart_the_caller_may_not_read_stays_out_of_their_image(self):
        """The key opens every chart on the dashboard. A User Permission that
        limits the reader to one query must still keep the other chart out."""
        self.narrow_to_query(READER, self.query)
        self.assertEqual(self.draw(READER), {"Image Chart": READER_TODOS})

    # @feature dashboard.image
    def test_a_caller_who_may_not_read_the_dashboard_gets_no_image(self):
        with self.assertRaises(frappe.PermissionError):
            self.draw(OUTSIDER)

    # @feature dashboard.image
    def test_a_guest_gets_no_image(self):
        frappe.set_user("Guest")
        self.addCleanup(frappe.set_user, "Administrator")
        with self.assertRaises(frappe.PermissionError):
            execute_cmd("insights.api.view.get_dashboard_image")

    # @feature dashboard.image
    def test_a_frappe_that_cannot_capture_a_whole_page_draws_nothing(self):
        """Without a whole-page capture the image would be the top of the page,
        and Frappe v15's fallback sends the page to an outside service."""

        def top_of_the_page_only(url, wait_for=0, headers=None, format="jpg"):
            raise AssertionError("captured")

        with (
            as_user(OWNER),
            patch("frappe.utils.preview.get_preview_from_url", top_of_the_page_only),
            self.assertRaises(frappe.ValidationError),
        ):
            get_dashboard_image(self.dashboard)
