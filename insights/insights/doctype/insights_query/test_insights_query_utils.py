# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest
from pypika import Table, Case
from insights.insights.doctype.insights_query.utils import parse_query_expression


class TestQueryUtils(unittest.TestCase):
    pass


class TestParseExpression(unittest.TestCase):
    def test_column(self):
        tree = {
            "type": "Column",
            "value": {"table": "Car", "column": "price"},
        }
        column = parse_query_expression(tree)
        self.assertEqual(column.table, Table("Car"))
        self.assertEqual(column.name, "price")

    def test_add_expression(self):
        tree = {
            "type": "BinaryExpression",
            "operator": "+",
            "left": {
                "type": "Column",
                "value": {"table": "Car", "column": "price"},
            },
            "right": {
                "type": "Number",
                "value": 100,
            },
        }
        expression = parse_query_expression(tree)
        self.assertEqual(expression.left.table, Table("Car"))
        self.assertEqual(expression.left.name, "price")
        self.assertEqual(expression.operator.value, "+")
        self.assertEqual(expression.right.value, 100)

    def test_aggregation_expression(self):
        aggregations = ["count", "sum", "min", "max", "avg", "distinct"]
        for aggregation in aggregations:
            tree = {
                "type": "CallExpression",
                "function": aggregation,
                "arguments": [
                    {
                        "type": "Column",
                        "value": {"table": "Car", "column": "price"},
                    },
                ],
            }
            agg_column = parse_query_expression(tree)
            self.assertEqual(agg_column.name.lower(), aggregation)
            self.assertEqual(agg_column.args[0].table, Table("Car"))
            self.assertEqual(agg_column.args[0].name, "price")

    def test_conditional_aggregation(self):
        tree = {
            "type": "CallExpression",
            "function": "count_if",
            "arguments": [
                {
                    "type": "BinaryExpression",
                    "operator": ">",
                    "left": {
                        "type": "Column",
                        "value": {"table": "Car", "column": "price"},
                    },
                    "right": {
                        "type": "Number",
                        "value": 100,
                    },
                },
            ],
        }
        agg_column = parse_query_expression(tree)
        self.assertEqual(agg_column.name.lower(), "sum")
        self.assertEqual(type(agg_column.args[0]), Case)

    def test_single_args_functions(self):
        single_arg_functions = [
            "abs",
            "floor",
            "lower",
            "upper",
            "concat",
            "ceil",
            "round",
            "count",
            "distinct",
        ]

        for function in single_arg_functions:
            tree = {
                "type": "CallExpression",
                "function": function,
                "arguments": [
                    {
                        "type": "Column",
                        "value": {"table": "Car", "column": "price"},
                    },
                ],
            }
            agg_column = parse_query_expression(tree)
            self.assertEqual(agg_column.name.lower(), function)
            self.assertEqual(agg_column.args[0].table, Table("Car"))
            self.assertEqual(agg_column.args[0].name, "price")

    def test_if_null_function(self):
        tree = {
            "type": "CallExpression",
            "function": "if_null",
            "arguments": [
                {
                    "type": "Column",
                    "value": {"table": "Car", "column": "price"},
                },
                {
                    "type": "Number",
                    "value": 100,
                },
            ],
        }
        agg_column = parse_query_expression(tree)
        self.assertEqual(agg_column.name, "IFNULL")
        self.assertEqual(agg_column.args[0].table, Table("Car"))
        self.assertEqual(agg_column.args[0].name, "price")
        self.assertEqual(agg_column.args[1].value, 100)

    def test_coalesce_function(self):
        tree = {
            "type": "CallExpression",
            "function": "coalesce",
            "arguments": [
                {
                    "type": "Column",
                    "value": {"table": "Car", "column": "price"},
                },
                {
                    "type": "Column",
                    "value": {"table": "Car", "column": "mrp"},
                },
                {
                    "type": "Number",
                    "value": 100,
                },
            ],
        }
        agg_column = parse_query_expression(tree)
        self.assertEqual(agg_column.name.lower(), "coalesce")
        self.assertEqual(agg_column.args[0].table, Table("Car"))
        self.assertEqual(agg_column.args[0].name, "price")
        self.assertEqual(agg_column.args[1].table, Table("Car"))
        self.assertEqual(agg_column.args[1].name, "mrp")
        self.assertEqual(agg_column.args[2].value, 100)

    def test_between_function(self):
        tree = {
            "type": "CallExpression",
            "function": "between",
            "arguments": [
                {
                    "type": "Column",
                    "value": {"table": "Car", "column": "price"},
                },
                {
                    "type": "Number",
                    "value": 100,
                },
                {
                    "type": "Number",
                    "value": 200,
                },
            ],
        }
        expression = parse_query_expression(tree)
        self.assertEqual(expression.get_sql().lower(), "price between 100 and 200")

    def test_contains_function(self):
        tree = {
            "type": "CallExpression",
            "function": "contains",
            "arguments": [
                {
                    "type": "Column",
                    "value": {"table": "Car", "column": "model"},
                },
                {
                    "type": "String",
                    "value": "Audi",
                },
            ],
        }
        expression = parse_query_expression(tree)
        self.assertTrue(expression.get_sql().lower(), "like '%audi%'")

    def test_replace_function(self):
        tree = {
            "type": "CallExpression",
            "function": "replace",
            "arguments": [
                {
                    "type": "Column",
                    "value": {"table": "Car", "column": "model"},
                },
                {
                    "type": "String",
                    "value": "Audi",
                },
                {
                    "type": "String",
                    "value": "BMW",
                },
            ],
        }
        expression = parse_query_expression(tree)
        self.assertEqual(expression.name.lower(), "replace")
        self.assertEqual(expression.args[0].table, Table("Car"))
        self.assertEqual(expression.args[0].name, "model")
        self.assertEqual(expression.args[1].value, "Audi")
        self.assertEqual(expression.args[2].value, "BMW")

    def test_case_function(self):
        tree = {
            "type": "CallExpression",
            "function": "case",
            "arguments": [
                {
                    "type": "BinaryExpression",
                    "operator": "<",
                    "left": {
                        "type": "Column",
                        "value": {"table": "Car", "column": "price"},
                    },
                    "right": {
                        "type": "Number",
                        "value": 300_000,
                    },
                },
                {
                    "type": "String",
                    "value": "Low Price",
                },
            ],
        }
        self.assertRaises(frappe.ValidationError, parse_query_expression, tree)

        tree = {
            "type": "CallExpression",
            "function": "case",
            "arguments": [
                {
                    "type": "BinaryExpression",
                    "operator": "<",
                    "left": {
                        "type": "Column",
                        "value": {"table": "Car", "column": "price"},
                    },
                    "right": {
                        "type": "Number",
                        "value": 300_000,
                    },
                },
                {
                    "type": "String",
                    "value": "Low Price",
                },
                {
                    "type": "BinaryExpression",
                    "operator": ">",
                    "left": {
                        "type": "Column",
                        "value": {"table": "Car", "column": "price"},
                    },
                    "right": {
                        "type": "Number",
                        "value": 500_000,
                    },
                },
                {
                    "type": "String",
                    "value": "High Price",
                },
                {
                    "type": "String",
                    "value": "Usual Price",
                },
            ],
        }
        expression = parse_query_expression(tree)
        self.assertEqual(type(expression), Case)
        self.assertEqual(
            expression.get_sql().lower().replace('"', ""),
            "case when price<300000 then 'low price' when price>500000 then 'high price' else 'usual price' end",
        )
