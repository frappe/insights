# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

from insights.insights.doctype.insights_data_source_v3.data_warehouse import UNUSED_TABLE_DAYS
from insights.insights.doctype.insights_query_execution_log.insights_query_execution_log import (
    InsightsQueryExecutionLog,
)


class TestInsightsQueryExecutionLog(FrappeTestCase):
    def setUp(self):
        frappe.db.delete("Insights Query Execution Log")

    def create_log(self, days_ago):
        doc = frappe.get_doc({"doctype": "Insights Query Execution Log", "sql": "select 1"}).insert()
        creation = add_days(now_datetime(), -days_ago)
        frappe.db.set_value(doc.doctype, doc.name, "creation", creation, update_modified=False)
        return doc.name

    def test_clears_logs_older_than_retention(self):
        old = self.create_log(100)
        recent = self.create_log(10)

        InsightsQueryExecutionLog.clear_old_logs(90)

        self.assertFalse(frappe.db.exists("Insights Query Execution Log", old))
        self.assertTrue(frappe.db.exists("Insights Query Execution Log", recent))

    def test_keeps_history_needed_by_data_store_cleanup(self):
        # prune_unused_tables skips pruning unless the log is older than UNUSED_TABLE_DAYS
        beyond_window = self.create_log(UNUSED_TABLE_DAYS + 1)

        InsightsQueryExecutionLog.clear_old_logs(1)

        self.assertTrue(frappe.db.exists("Insights Query Execution Log", beyond_window))
