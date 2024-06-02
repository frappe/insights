# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

test_dependencies = ("Insights Data Source", "Insights Table")
test_records = frappe.get_test_records("Insights Query")


class TestInsightsQuery(FrappeTestCase):
    pass
