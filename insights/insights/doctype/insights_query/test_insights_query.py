# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import frappe
from frappe.tests.utils import FrappeTestCase

test_dependencies = ("Insights Data Source", "Insights Table")
test_records = frappe.get_test_records("Insights Query")


class TestInsightsQuery(FrappeTestCase):
    def test_todo_count_with_filters(self):
        frappe.db.delete("ToDo")
        for i in range(10):
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"Test {i}",
                    "status": "Open" if i % 2 == 0 else "Closed",
                }
            )
            todo.insert()
        frappe.db.commit()
        test_records[0]["filters"] = json.dumps(test_records[0]["filters"])
        query = frappe.get_doc(test_records[0])
        query.save()
        query.build_and_execute()
        query.save()

        self.assertTrue("count(*)" in query.sql.lower())
        self.assertTrue("`status`='Open'" in query.sql)
        self.assertTrue("5" in query.result)

        column_values = query.fetch_column_values(
            {"table": "tabToDo", "column": "status"}
        )
        self.assertTrue(len(column_values), 2)
        self.assertTrue("Open" in column_values)
        self.assertTrue("Closed" in column_values)

    def test_todo_by_creation(self):
        frappe.db.delete("ToDo")
        for i in range(10):
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"Test {i}",
                    "status": "Open",
                    "date": frappe.utils.add_days(frappe.utils.nowdate(), i),
                }
            )
            todo.insert()
        frappe.db.commit()

        # create an insights query to get the count of todos by due date
        query = frappe.get_doc(test_records[1])
        query.save()
        query.build_and_execute()
        query.save()

        self.assertEqual(len(json.loads(query.result)), 11)
