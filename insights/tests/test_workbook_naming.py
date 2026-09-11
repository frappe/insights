"""A workbook exported before the naming change carries a numeric name.

`Insights Workbook` used to be named by `autoincrement`, so a fixture written on an
older site holds `"name": 12`. The column is varchar now, and `validate_name` throws
on an int. Such a fixture is already shipped in other apps, so the import has to keep
working (frappe/insights#1193).
"""

import frappe

from insights.tests.base import InsightsIntegrationTestCase


class TestWorkbookNaming(InsightsIntegrationTestCase):
    def test_numeric_name_is_stored_as_string(self):
        frappe.flags.in_import = True
        try:
            workbook = frappe.get_doc(
                {"doctype": "Insights Workbook", "name": 999999, "title": "Imported"}
            ).insert()
        finally:
            frappe.flags.in_import = False

        self.addCleanup(frappe.delete_doc, "Insights Workbook", workbook.name, force=True)
        self.assertEqual(workbook.name, "999999")
