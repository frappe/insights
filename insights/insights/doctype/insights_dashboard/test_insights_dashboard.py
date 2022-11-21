# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase

from .insights_dashboard import get_item_position


class TestInsightsDashboard(FrappeTestCase):
    def test_new_item_position(self):
        new_item = {"item_type": "Chart", "layout": {"w": 12, "h": 9}}
        existing_layouts = [
            {"x": 0, "y": 0, "w": 6, "h": 6},
            {"x": 6, "y": 0, "w": 6, "h": 6},
            {"x": 0, "y": 6, "w": 6, "h": 6},
        ]
        layout = get_item_position(new_item, existing_layouts)
        self.assertEqual(layout, {"x": 12, "y": 0, "w": 12, "h": 9})
