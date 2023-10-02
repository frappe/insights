# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from insights.api.data_sources import fetch_column_values

test_dependencies = ("Insights Data Source", "Insights Table")
test_records = frappe.get_test_records("Insights Query")


class TestInsightsQuery(FrappeTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_source = "Site DB"

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
        query.data_source = self.data_source
        query.save()
        query.fetch_results()
        query.save()

        self.assertTrue("count(*)" in query.sql.lower())
        self.assertTrue("status = 'Open'" in query.sql)
        self.assertTrue("5" in query.results)

        doc = frappe.get_doc("Insights Data Source", self.data_source)
        column_values = doc.get_column_options("tabToDo", "Status")
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
        query.data_source = self.data_source
        query.save()
        query.fetch_results()
        query.save()

        self.assertEqual(len(json.loads(query.results)), 11)

    def test_pivot_transform(self):
        frappe.db.delete("ToDo")
        reference_types = ["User", "Report", "Error Log", "Server Script"]
        for i in range(10):
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"Test {i}",
                    "status": "Open" if i % 2 == 0 else "Closed",
                    "reference_type": reference_types[i % 4],
                }
            )
            todo.insert()
        frappe.db.commit()

        query = frappe.get_doc(test_records[3])
        query.data_source = self.data_source
        query.save()
        query.fetch_results()
        result = json.loads(query.results)
        self.assertEqual(len(result), 5)
        self.assertEqual(len(result[0]), 3)

        query.add_transform(
            "Pivot", {"index": "Status", "column": "Reference Type", "value": "Count"}
        )
        result = json.loads(query.results)
        self.assertEqual(len(result), 3)
        self.assertEqual(len(result[0]), 5)

    def test_cumulative_count(self):
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
        query.data_source = self.data_source
        query.append(
            "columns",
            {
                "column": "*",
                "type": "Integer",
                "table": "tabToDo",
                "table_label": "ToDo",
                "label": "Cumulative Count",
                "aggregation": "Cumulative Count",
            },
        )
        query.save()
        query.fetch_results()
        query.save()
        print(query.status)
        result = json.loads(query.results)
        self.assertEqual(len(result), 11)
        self.assertEqual(result[-1][2], 10)


class TestInsightsQueryBuilder(FrappeTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_source = "Site DB"

    def test_no_arg_function(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        for func in ["now", "today"]:
            expression = make_call_expression(func)
            query.append("columns", make_query_column_expression(expression))
        query.save().fetch_results()

    def test_single_arg_function(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        for func in [
            "sum",
            "avg",
            "min",
            "max",
            "count",
            "abs",
            "round",
            "floor",
            "ceil",
            "lower",
            "upper",
            "is_set",
            "is_not_set",
        ]:
            expression = make_call_expression(func, make_todo_column("docstatus"))
            query.append("columns", make_query_column_expression(expression))
        query.save().fetch_results()

    def test_conditional_arg_function(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        for func in ["sum_if", "count_if", "if_null"]:
            expression = make_call_expression(
                func,
                make_binary_expression(make_todo_column("docstatus"), "=", make_number(1)),
                make_todo_column("docstatus"),
            )
            query.append("columns", make_query_column_expression(expression))
        query.save().fetch_results()

    def test_two_arg_function(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        for func in [
            "contains",
            "not_contains",
            "ends_with",
            "starts_with",
        ]:
            expression = make_call_expression(
                func, make_todo_column("description"), make_string("Test")
            )
            query.append("columns", make_query_column_expression(expression))

    def test_three_arg_function(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        for func in ["between", "replace", "concat", "coalesce"]:
            expression = make_call_expression(
                func, make_todo_column("docstatus"), make_string("0"), make_string("1")
            )
            query.append("columns", make_query_column_expression(expression))
        query.save().fetch_results()

    def test_in_operator(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        for func in ["in", "not_in"]:
            expression = make_call_expression(
                func,
                make_todo_column("docstatus"),
                make_string("0"),
                make_string("1"),
                make_string("2"),
            )
            query.append("columns", make_query_column_expression(expression))
        query.save().fetch_results()

    def test_case_when(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        expression = make_call_expression(
            "case",
            make_binary_expression(make_todo_column("docstatus"), "=", make_number(1)),
            make_string("Open"),
            make_string("Closed"),
        )
        query.append("columns", make_query_column_expression(expression))
        query.save().fetch_results()

    def test_timespan_function(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        expression = make_call_expression(
            "timespan",
            make_todo_column("date"),
            make_string("Last 1 Years"),
        )
        query.append("columns", make_query_column_expression(expression))
        query.save().fetch_results()

    def test_time_elapsed_function(self):
        query = frappe.get_doc(test_records[2])
        query.data_source = self.data_source
        expression = make_call_expression(
            "time_elapsed",
            make_string("DAY"),
            make_todo_column("date"),
            make_string("2021-01-01"),
        )
        query.append("columns", make_query_column_expression(expression))
        query.save().fetch_results()


def make_query_column_expression(expression):
    return {
        "label": random_string(5),
        "column": "Test",
        "is_expression": 1,
        "expression": expression,
    }


def make_todo_column(column):
    return {
        "type": "Column",
        "value": {"table": "tabToDo", "column": column},
    }


def make_call_expression(func, *args):
    return {
        "raw": "sum(`tabToDo.docstatus`)",
        "ast": {
            "type": "CallExpression",
            "function": func,
            "arguments": args,
        },
    }


def make_binary_expression(left, operator, right):
    return {
        "type": "BinaryExpression",
        "operator": operator,
        "left": left,
        "right": right,
    }


def make_number(value):
    return {
        "type": "Number",
        "value": value,
    }


def make_string(value):
    return {
        "type": "String",
        "value": value,
    }


class TestInsightsQueryBuilderWithSQLite(TestInsightsQueryBuilder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_source = "Test SQLite DB"

    def test_todo_count_with_filters(self):
        # skip the test as it tests the results of the query
        # SQLite DB doesn't have data in tabToDo table
        pass

    def test_todo_by_creation(self):
        # skip the test as it tests the results of the query
        # SQLite DB doesn't have data in tabToDo table
        pass
