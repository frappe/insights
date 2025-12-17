import unittest

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections


class TestBasicWorkflow(unittest.TestCase):
    def test_query_execution(self):
        ds = frappe.get_all("Insights Data Source v3", pluck="name")
        self.assertTrue(len(ds) > 0, "No Data Sources found")
        self.assertIn("Site DB", ds, "Site DB Data Source not found")

        w = frappe.new_doc("Insights Workbook")
        w.title = "Basic Workflow Test"
        w.insert()

        q = frappe.new_doc("Insights Query v3")
        q.title = "tabToDo"
        q.workbook = w.name
        q.use_live_connection = 1
        q.is_builder_query = 1
        q.operations = [
            {
                "type": "source",
                "table": {
                    "type": "table",
                    "data_source": "Site DB",
                    "table_name": "tabToDo",
                },
            }
        ]
        q.insert()

        with db_connections():
            q.execute()

        q.delete()
        w.delete()
