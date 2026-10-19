"""What the preview browser opens, and what its key opens in return.

Generating a preview image starts a browser on the server and hands it a key,
because the dashboard it renders is not public. Two things follow. The page it
opens must be this site's, not one a request header named. And the key must open
the documents that image already shows, not every document a public link could.
"""

import io
from unittest.mock import patch

import frappe
from PIL import Image
from werkzeug.test import EnvironBuilder

from insights.api.view import get_dashboard
from insights.permission_user import permission_user_for
from insights.permissions import has_doc_permission
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
            return bool(has_doc_permission(frappe.get_doc(doctype, name), "read", "Guest"))
        finally:
            frappe.local.request = request_was

    def as_render(self, key, run):
        """Run `run` the way the preview browser does: as Guest, with the key."""
        request_was = frappe.local.request
        user_was = frappe.session.user
        frappe.local.request = EnvironBuilder(headers={"X-Insights-Preview-Key": key}).get_request()
        frappe.set_user("Guest")
        try:
            return run()
        finally:
            frappe.set_user(user_was)
            frappe.local.request = request_was

    def render(self, dashboard):
        """Run a preview and return the URL opened and the key it passed."""
        opened = {}

        def record(url, headers=None):
            opened["url"] = url
            opened["key"] = (headers or {})["X-Insights-Preview-Key"]
            # what the browser sees when it comes back with the key
            opened["reads"] = {
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
            # the preview page loads through the viewer like any other reader,
            # and its charts run as the user the key was made for
            opened["viewer_title"] = self.as_render(
                opened["key"], lambda: get_dashboard(self.dashboard)["title"]
            )
            opened["runs_as"] = {
                name: self.as_render(
                    opened["key"],
                    lambda name=name: permission_user_for(frappe.get_doc(DT.CHART, name)),
                )
                for name in (self.chart, self.other_chart)
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

    # @feature dashboard.preview-image
    def test_the_browser_opens_this_site(self):
        self.assertNotIn(ATTACKER_HOST, self.render(self.dashboard)["url"])

    # @feature dashboard.preview-image
    def test_the_key_opens_the_dashboard_being_previewed(self):
        reads = self.render(self.dashboard)["reads"]
        self.assertTrue(reads[(DT.DASHBOARD, self.dashboard)])
        self.assertTrue(reads[(DT.CHART, self.chart)])
        self.assertTrue(reads[(DT.QUERY, self.query)])

    # @feature dashboard.preview-image
    def test_the_key_opens_nothing_else(self):
        reads = self.render(self.dashboard)["reads"]
        self.assertFalse(reads[(DT.DASHBOARD, self.other_dashboard)])
        self.assertFalse(reads[(DT.CHART, self.other_chart)])
        self.assertFalse(reads[(DT.QUERY, self.other_query)])

    # @feature dashboard.preview-image
    def test_the_previewed_page_reads_through_the_viewer(self):
        self.assertEqual(self.render(self.dashboard)["viewer_title"], "Preview Dashboard")

    # @feature dashboard.preview-image
    def test_the_render_runs_as_the_user_the_key_was_cut_for(self):
        runs_as = self.render(self.dashboard)["runs_as"]
        self.assertEqual(runs_as[self.chart], "Administrator")
        # a chart the key does not open runs as the caller
        self.assertEqual(runs_as[self.other_chart], "Guest")

    # @feature dashboard.preview-image
    def test_a_spent_key_opens_nothing(self):
        opened = self.render(self.dashboard)
        frappe.local.request = EnvironBuilder(headers={"X-Insights-Preview-Key": opened["key"]}).get_request()
        dashboard = frappe.get_doc(DT.DASHBOARD, self.dashboard)
        self.assertFalse(has_doc_permission(dashboard, "read", "Guest"))

    # @feature dashboard.preview-image
    def test_an_apps_dashboard_renders_no_preview(self):
        """A preview shows its renderer's rows to every reader, and an app's
        dashboard is read by roles whose members may see other rows."""
        frappe.db.set_value(DT.WORKBOOK, self.other_workbook, "is_standard", 1)
        self.addCleanup(frappe.db.set_value, DT.WORKBOOK, self.other_workbook, "is_standard", 0)
        self.assertEqual(self.render(self.other_dashboard), {})

    # @feature dashboard.preview-image
    def test_the_patch_deletes_the_preview_file_of_an_apps_dashboard(self):
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            create_preview_file,
        )
        from insights.patches import clear_standard_dashboard_previews

        image = io.BytesIO()
        Image.new("RGB", (2, 2)).save(image, "JPEG")
        file_url = create_preview_file(image.getvalue(), self.other_dashboard)
        frappe.db.set_value(DT.DASHBOARD, self.other_dashboard, "preview_image", f"{file_url}?ab12")
        frappe.db.set_value(DT.WORKBOOK, self.other_workbook, "is_standard", 1)
        self.addCleanup(frappe.db.set_value, DT.WORKBOOK, self.other_workbook, "is_standard", 0)

        clear_standard_dashboard_previews.execute()

        self.assertIsNone(frappe.db.get_value(DT.DASHBOARD, self.other_dashboard, "preview_image"))
        self.assertFalse(frappe.db.exists("File", {"file_url": file_url}))

    # @feature dashboard.preview-image
    def test_a_page_that_does_not_answer_is_not_captured(self):
        """Chromium captures its own error page, which was saved as the preview."""
        import requests

        from insights.insights.doctype.insights_dashboard_v3 import insights_dashboard_v3

        with (
            patch.object(requests, "get", side_effect=requests.ConnectionError("refused")),
            patch("frappe.utils.preview.get_preview_from_url", return_value=b"error page") as capture,
        ):
            with self.assertRaises(frappe.ValidationError):
                insights_dashboard_v3.get_page_preview("http://site.localhost:8000/insights/shared/x")

        capture.assert_not_called()
