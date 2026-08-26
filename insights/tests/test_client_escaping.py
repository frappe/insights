"""Rules the client templates hold, checked against their source.

The app has no JavaScript test runner, and these rules live in one line of one
template each. A source check is a poorer test than a rendered one, and it is
what keeps the rule from being undone by a later edit.
"""

import re
from pathlib import Path

from frappe.tests import UnitTestCase

import insights

APP = Path(insights.__file__).parent.parent


class TestErrorToastRendersText(UnitTestCase):
    """A toast shows what the server said, so it shows it as text.

    The message reaches the toast from a server error, and a server error
    repeats input the caller never chose — a column name, a table name, a title
    somebody else wrote. Frappe sanitizes its own display copy and Insights
    reads the raw traceback line instead, so the toast is where this stops.
    """

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
        reads = re.findall(r"(\S{0,14})\s*frm\.doc\.label", form)
        self.assertTrue(reads, "the form no longer reads the label")
        for read in reads:
            self.assertIn("escape_html(", read)
