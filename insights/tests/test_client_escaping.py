"""The client renders what the server sent, and it renders it as text.

A toast message is a server error line, and a server error repeats input the
caller never chose — a column name, a table name, a title somebody else wrote.

The app has no JavaScript test runner. A source check is a poorer test than a
rendered one, and it is what keeps the rule from being undone by a later edit.
"""

import re
from pathlib import Path

from frappe.tests import UnitTestCase

import insights

APP = Path(insights.__file__).parent.parent


class TestErrorToastRendersText(UnitTestCase):
    """The toast renders what the server sent, so it renders it as text."""

    def test_the_toast_renders_no_html(self):
        toast = (APP / "frontend/src2/components/Toast.vue").read_text()
        self.assertNotIn("v-html", toast)


class TestDeskFormEscapesTheTableLabel(UnitTestCase):
    """The table label is a value, so the desk form escapes it before it renders.

    `__()` substitution is plain `{0}` replacement with no escaping, and both
    `frappe.confirm` and a dialog title append what it produces as HTML.
    """

    def test_every_read_of_the_label_is_escaped(self):
        form = (APP / "insights/insights/doctype/insights_table_v3/insights_table_v3.js").read_text()
        # Collapsed, so a reformat that rewraps the call cannot fail the rule.
        form = re.sub(r"\s+", " ", form)
        reads = re.findall(r"(\S{0,14} )?frm\.doc\.label", form)
        self.assertTrue(reads, "the form no longer reads the label")
        for read in reads:
            self.assertIn("escape_html(", read)
