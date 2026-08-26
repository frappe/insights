"""The client renders what the server sent, and it renders it as text.

A toast message is a server error line, and a server error repeats input the
caller never chose — a column name, a table name, a title somebody else wrote.

The app has no JavaScript test runner. A source check is a poorer test than a
rendered one, and it is what keeps the rule from being undone by a later edit.
"""

from pathlib import Path

from frappe.tests import UnitTestCase

import insights

APP = Path(insights.__file__).parent.parent


class TestErrorToastRendersText(UnitTestCase):
    """The toast renders what the server sent, so it renders it as text."""

    def test_the_toast_renders_no_html(self):
        toast = (APP / "frontend/src2/components/Toast.vue").read_text()
        self.assertNotIn("v-html", toast)
