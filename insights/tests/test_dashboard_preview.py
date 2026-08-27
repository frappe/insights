"""What the preview browser opens, and what its key opens in return.

Generating a preview image starts a browser on the server and hands it a key,
because the dashboard it renders is not public. Two things follow. The page it
opens must be this site's, not one a request header named. And the key must open
the documents that image already shows, not every document a public link could.
"""

from unittest.mock import patch

import frappe
from werkzeug.test import EnvironBuilder

from insights.api.shared import is_public
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import USER_1, create_test_users

OWNER = USER_1
ATTACKER_HOST = "attacker.example"


class TestDashboardPreview(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title="Preview Workbook").name
        cls.query = create_test_query(OWNER, cls.workbook, title="Preview Query").name
        cls.chart = create_test_chart(OWNER, cls.workbook, query=cls.query, title="Preview Chart").name
        cls.dashboard = create_test_dashboard(
            OWNER, cls.workbook, chart=cls.chart, title="Preview Dashboard"
        ).name

        cls.other_workbook = create_test_workbook(OWNER, title="Unpreviewed Workbook").name
        cls.other_query = create_test_query(OWNER, cls.other_workbook, title="Unpreviewed Query").name
        cls.other_chart = create_test_chart(
            OWNER, cls.other_workbook, query=cls.other_query, title="Unpreviewed Chart"
        ).name
        cls.other_dashboard = create_test_dashboard(
            OWNER, cls.other_workbook, chart=cls.other_chart, title="Unpreviewed Dashboard"
        ).name

    @classmethod
    def after_class(cls):
        for workbook in (cls.workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, workbook, force=True, ignore_permissions=True)
        delete_users(OWNER)

    def before_test(self):
        self.request_was = getattr(frappe.local, "request", None)
        self.addCleanup(setattr, frappe.local, "request", self.request_was)
        frappe.local.request = EnvironBuilder(headers={"Host": ATTACKER_HOST}).get_request()

    def reads_with_key(self, key, doctype, name):
        request_was = frappe.local.request
        frappe.local.request = EnvironBuilder(headers={"X-Insights-Preview-Key": key}).get_request()
        try:
            return bool(is_public(doctype, name))
        finally:
            frappe.local.request = request_was

    def render(self, dashboard):
        """Run a preview and return the URL opened and the key it carried."""
        opened = {}

        def record(url, headers=None):
            opened["url"] = url
            opened["key"] = (headers or {})["X-Insights-Preview-Key"]
            # what the browser sees when it comes back with the key
            opened["public"] = {
                (doctype, name): self.reads_with_key(opened["key"], doctype, name)
                for doctype, name in (
                    (DT.DASHBOARD, self.dashboard),
                    (DT.CHART, self.chart),
                    (DT.QUERY, self.query),
                    (DT.DASHBOARD, self.other_dashboard),
                    (DT.CHART, self.other_chart),
                    (DT.QUERY, self.other_query),
                )
            }
            return b"preview"

        doc = frappe.get_doc(DT.DASHBOARD, dashboard)
        with (
            patch(
                "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.get_page_preview",
                side_effect=record,
            ),
            patch(
                "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.create_preview_file",
                return_value="/files/preview.jpeg",
            ),
        ):
            doc.generate_dashboard_preview()
        return opened

    def test_the_browser_opens_this_site(self):
        self.assertNotIn(ATTACKER_HOST, self.render(self.dashboard)["url"])

    def test_the_key_opens_the_dashboard_being_previewed(self):
        public = self.render(self.dashboard)["public"]
        self.assertTrue(public[(DT.DASHBOARD, self.dashboard)])
        self.assertTrue(public[(DT.CHART, self.chart)])
        self.assertTrue(public[(DT.QUERY, self.query)])

    def test_the_key_opens_nothing_else(self):
        public = self.render(self.dashboard)["public"]
        self.assertFalse(public[(DT.DASHBOARD, self.other_dashboard)])
        self.assertFalse(public[(DT.CHART, self.other_chart)])
        self.assertFalse(public[(DT.QUERY, self.other_query)])

    def test_a_spent_key_opens_nothing(self):
        opened = self.render(self.dashboard)
        frappe.local.request = EnvironBuilder(headers={"X-Insights-Preview-Key": opened["key"]}).get_request()
        self.assertFalse(is_public(DT.DASHBOARD, self.dashboard))
