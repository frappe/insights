# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import unittest

import frappe

from .demo import SAMPLE_WORKBOOK_TITLE, DemoDataFactory


class TestDemoSetup(unittest.TestCase):
    # @feature settings.demo-data
    def test_import_demo_data(self):
        factory = DemoDataFactory().run()
        self.assertTrue(factory.demo_data_exists())

    # @feature settings.demo-data
    def test_setting_up_demo_data_returns_the_sample_workbook_to_open(self):
        from .setup_wizard import setup_demo_data

        workbook = setup_demo_data()
        self.assertEqual(frappe.db.get_value("Insights Workbook", workbook, "title"), SAMPLE_WORKBOOK_TITLE)

    # @feature settings.demo-data
    def test_demo_data_is_offered_until_the_site_has_a_workbook_of_its_own(self):
        """A workbook an app ships is not the site's own."""
        from insights.api import get_user_info

        frappe.db.savepoint("own_workbooks")
        self.addCleanup(frappe.db.rollback, save_point="own_workbooks")
        frappe.db.delete("Insights Workbook", {"is_standard": 0})
        self.assertFalse(get_user_info()["has_workbooks"])

        frappe.get_doc({"doctype": "Insights Workbook", "title": "Own Workbook"}).insert()
        self.assertTrue(get_user_info()["has_workbooks"])
