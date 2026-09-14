"""The client renders what the server sent, and it renders it as text.

A server message repeats input the caller never chose — a column name, a table
name, a title somebody else wrote.

What is left here is the desk form, which is plain JavaScript no test runner
reaches. A source check is a poorer test than a rendered one, and it is what
keeps that one rule from being undone by a later edit. The app's own client is
under `frontend/`, where vitest runs.
"""

import re
from pathlib import Path

from frappe.tests import UnitTestCase

import insights

APP = Path(insights.__file__).parent.parent


class TestDeskFormEscapesTheTableLabel(UnitTestCase):
    """The table label is a value, so the desk form escapes it before it renders.

    `__()` substitution is plain `{0}` replacement with no escaping, and both
    `frappe.confirm` and a dialog title append what it produces as HTML.
    """

    # @feature data-source.table-label-is-text
    def test_every_read_of_the_label_is_escaped(self):
        form = (APP / "insights/insights/doctype/insights_table_v3/insights_table_v3.js").read_text()
        # Collapsed, so a reformat that rewraps the call cannot fail the rule.
        form = re.sub(r"\s+", " ", form)
        reads = re.findall(r"(\S{0,14} )?frm\.doc\.label", form)
        self.assertTrue(reads, "the form no longer reads the label")
        for read in reads:
            self.assertIn("escape_html(", read)
