"""Dashboard text is rich text, so it is stored as HTML that is safe to render.

A dashboard reaches readers the author never chose — anyone the workbook is
shared with, and every Guest who follows a public link. `items` is a JSON field,
which the framework's own sanitizer does not look inside, so the doctype does it.
"""

import frappe

from insights.patches.sanitize_dashboard_text import execute as sanitize_stored_text
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_workbook, delete_users
from insights.tests.permissions_utils import USER_1, create_test_users

OWNER = USER_1
PAYLOAD = "<img src=x onerror=alert(document.domain)>"
# a bare double-quoted string is valid JSON, which older sanitizers passed through
JSON_WRAPPED_PAYLOAD = f'"{PAYLOAD}"'


class TestDashboardText(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title="Text Workbook").name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(OWNER)

    def stored_text(self, text):
        with self.as_user(OWNER):
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Text Dashboard",
                    "workbook": self.workbook,
                    "items": [{"id": "text-1", "type": "text", "text": text}],
                }
            ).insert()
        self.addCleanup(frappe.delete_doc, DT.DASHBOARD, dashboard.name, force=True)
        return frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items"))[0]["text"]

    def test_an_event_handler_does_not_survive_a_save(self):
        self.assertNotIn("onerror", self.stored_text(PAYLOAD))

    def test_wrapping_the_payload_in_quotes_does_not_smuggle_it_through(self):
        self.assertNotIn("onerror", self.stored_text(JSON_WRAPPED_PAYLOAD))

    def test_ordinary_rich_text_is_kept(self):
        stored = self.stored_text('<p>Revenue is <b>up</b>. <a href="/app">Details</a></p>')
        self.assertIn("<b>up</b>", stored)
        self.assertIn('href="/app"', stored)

    def test_text_stored_before_the_rule_is_sanitized_in_place(self):
        with self.as_user(OWNER):
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Legacy Text Dashboard",
                    "workbook": self.workbook,
                    "items": [{"id": "text-1", "type": "text", "text": "clean"}],
                }
            ).insert()
        self.addCleanup(frappe.delete_doc, DT.DASHBOARD, dashboard.name, force=True)
        frappe.db.set_value(
            DT.DASHBOARD,
            dashboard.name,
            "items",
            frappe.as_json([{"id": "text-1", "type": "text", "text": PAYLOAD}]),
            update_modified=False,
        )

        sanitize_stored_text()

        items = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items"))
        self.assertNotIn("onerror", items[0]["text"])
