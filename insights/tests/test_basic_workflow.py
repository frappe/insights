import unittest

import frappe


class TestBasicWorkflow(unittest.TestCase):
    def test_query_execution(self):
        q = frappe.new_doc("Insights Query v3")
        q.title = "tabToDo"
        q.use_live_connection = 1
        q.is_builder_query = 1
        q.operations = [
            {
                "table": {
                    "data_source": "Site DB",
                    "table_name": "tabToDo",
                    "type": "table",
                },
                "type": "source",
            }
        ]
        q.insert()
        q.execute()
