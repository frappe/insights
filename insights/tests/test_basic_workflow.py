import unittest

import frappe


class TestBasicWorkflow(unittest.TestCase):
    def test_query_execution(self):
        ds = frappe.get_all("Insights Data Source", pluck="name")
        self.assertTrue(len(ds) > 0, "No Data Sources found")
        self.assertIn("Site DB", ds, "Site DB Data Source not found")

        frappe.db.delete("ToDo")
        for i in range(5):
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"Test {i}",
                    "status": "Open",
                }
            )
            todo.insert()
        frappe.db.commit()

        query = frappe.get_doc(
            {
                "doctype": "Insights Query",
                "title": "Test Todo Count",
                "data_source": "Site DB",
                "columns": [
                    {
                        "label": "Count",
                        "type": "Integer",
                        "table": "tabToDo",
                        "table_label": "ToDo",
                        "aggregation": "Count",
                        "column": "*",
                        "doctype": "Insights Query Column",
                    }
                ],
                "tables": [
                    {
                        "label": "ToDo",
                        "table": "tabToDo",
                        "doctype": "Insights Query Table",
                    }
                ],
            }
        )
        query.save()
        query.fetch_results()
        query.save()

        self.assertTrue(query.results_row_count == 5, "Query did not return expected number of rows")
