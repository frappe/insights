import unittest

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections


class TestBasicWorkflow(unittest.TestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_query_execution(self):
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
