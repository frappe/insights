"""Dashboard text is rich text, so it is stored as HTML that is safe to render.

A dashboard reaches readers the author never chose — anyone the workbook is
shared with, and every Guest who follows a public link. `items` is a JSON field,
which the framework's own sanitizer does not look inside, so the doctype does it.

Text stored before this rule is left alone. Rewriting it in place would delete
any `<iframe>` the editor put there, and there is no way back from that.
"""

import frappe

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

    def test_what_the_editor_writes_survives(self):
        """Measured against the marks `RichTextKit` emits, not a guess at them."""
        cases = {
            "marks": ("<b>up</b>", "<b>up</b>"),
            "link": ('<a href="/app">Details</a>', 'href="/app"'),
            "align": ('<p style="text-align:center">c</p>', "text-align:center"),
            "highlight": ('<mark data-color="yellow">n</mark>', '<mark data-color="yellow">'),
            "colour": ('<span style="color:rgb(255, 0, 0)">r</span>', "color:rgb(255, 0, 0)"),
            "table": ("<table><tbody><tr><td><p>c</p></td></tr></tbody></table>", "<td><p>c</p></td>"),
            "task": (
                '<ul data-type="taskList"><li data-checked="true" data-type="taskItem">'
                "<div><p>d</p></div></li></ul>",
                'data-type="taskItem"',
            ),
            "image": ('<img src="/files/a.png" alt="a">', 'src="/files/a.png"'),
            "mention": ('<span class="mention" data-id="a@b.com">@Ada</span>', 'data-id="a@b.com"'),
            "heading": ("<h2>Title</h2>", "<h2>Title</h2>"),
            "code": ('<pre><code class="language-sql">select 1</code></pre>', 'class="language-sql"'),
        }
        stored = self.stored_text("".join(markup for markup, _ in cases.values()))
        for name, (_, expected) in cases.items():
            with self.subTest(name):
                self.assertIn(expected, stored)

    def test_an_embed_does_not_survive(self):
        """The one thing the sanitizer removes outright. Pinned so it is a known
        cost of the rule and not a surprise."""
        self.assertNotIn("<iframe", self.stored_text('<iframe src="https://example.com"></iframe>'))
