# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from insights.tests.utils import (
    create_data_source,
    create_insights_query,
    create_insights_table,
    add_table,
    add_column,
)


class TestInsightsQuery(FrappeTestCase):
    def test_todo_count(self):
        frappe.db.delete("ToDo")
        for i in range(10):
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"Test {i}",
                    "status": "Open",
                }
            )
            todo.insert()
        frappe.db.commit()  # need to commit to get the correct count

        # create an insights query to get the count of todos
        data_source = create_data_source("Test Insights Query")
        create_insights_table("tabToDo", "ToDo", data_source.name)
        query = create_insights_query("Test Todo Count", data_source.name)
        add_table(query, "tabToDo")
        add_column(
            query, column=None, label="Count", aggregation="Count", table="tabToDo"
        )
        query.build_and_execute()
        query.save()

        self.assertTrue("count(*)" in query.sql.lower())
        self.assertTrue("10" in query.result)

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
        # create an insights query to get the count of open todos
        data_source = create_data_source("Test Insights Query")
        create_insights_table("tabToDo", "ToDo", data_source.name)
        query = create_insights_query("Test Todo Count", data_source.name)
        add_table(query, "tabToDo")
        add_column(
            query, column=None, label="Count", aggregation="Count", table="tabToDo"
        )
        query.update_filters(
            {
                "type": "LogicalExpression",
                "operator": "&&",
                "level": 1,
                "position": 1,
                "conditions": [
                    {
                        "type": "BinaryExpression",
                        "operator": "=",
                        "left": {
                            "type": "Column",
                            "value": {"column": "status", "table": "tabToDo"},
                        },
                        "right": {"type": "String", "value": "Open"},
                    }
                ],
            }
        )
        query.build_and_execute()
        query.save()

        self.assertTrue("count(*)" in query.sql.lower())
        self.assertTrue("`status`='Open'" in query.sql)
        self.assertTrue("5" in query.result)
