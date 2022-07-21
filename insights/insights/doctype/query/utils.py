# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import datetime
import operator

from typing import Tuple

import frappe
from frappe import _dict
from pypika import functions as fn
from frappe.query_builder import CustomFunction, functions, Case, Field, Table
from frappe.utils.data import (
    nowdate,
    add_to_date,
    get_first_day_of_week,
    get_last_day_of_week,
    get_first_day,
    get_last_day,
    get_quarter_start,
    get_quarter_ending,
    get_year_start,
    get_year_ending,
)


class Aggregations:
    @classmethod
    def get_aggregations(cls):
        return {
            "sum": functions.Sum,
            "min": functions.Min,
            "max": functions.Max,
            "avg": functions.Avg,
            "count": functions.Count,
            "sum_if": cls.sum_if,
            "count_if": cls.count_if,
            "distinct": CustomFunction("DISTINCT", ["column"]),
        }

    @classmethod
    def get_aggregation_function(cls, aggregation):
        return cls.get_aggregations()[aggregation]

    @staticmethod
    def sum_if(column, conditions):
        return functions.Sum(Case().when(conditions, column).else_(0))

    @staticmethod
    def count_if(conditions):
        return functions.Sum(Case().when(conditions, 1).else_(0))

    @classmethod
    def apply(cls, aggregation, *args, **kwargs):
        function = cls.get_aggregation_function(aggregation)
        if function:
            return function(*args, **kwargs)

        raise NotImplementedError(f"Aggregation {aggregation} not implemented")

    @classmethod
    def is_valid(cls, aggregation: str) -> bool:
        return aggregation in cls.get_aggregations()


class ColumnFormat:

    date_formats = {
        "Minute": "%D %M, %Y, %l:%i %p",
        "Hour": "%D %M, %Y, %l:00 %p",
        "Day": "%D %M, %Y",
        "Month": "%M, %Y",
        "Year": "%Y",
        "Minute of Hour": "%i",
        "Hour of Day": "%l:00 %p",
        "Day of Week": "%W",
        "Day of Month": "%D",
        "Day of Year": "%j",
        "Month of Year": "%M",
    }

    FormatDate = CustomFunction("DATE_FORMAT", ["date", "format"])
    ParseDate = CustomFunction("STR_TO_DATE", ["str", "format"])
    Quarter = CustomFunction("QUARTER", ["date"])

    @classmethod
    def format_date(cls, format, column):
        if format in cls.date_formats:
            _format = cls.date_formats[format]
            return cls.FormatDate(column, _format)
        elif format == "Quarter":
            quarter_of_year = fn.Concat("Q", cls.Quarter(column))
            year = cls.FormatDate(column, "%Y")
            return fn.Concat(quarter_of_year, ", ", year)
        elif format == "Quarter of Year":
            return cls.Quarter(column)

        return column

    @classmethod
    def parse_date(cls, format, column):
        if format in cls.date_formats:
            _format = cls.date_formats[format]
            return cls.ParseDate(column, _format)

        return column


class Operations:

    ARITHMETIC_OPERATIONS = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
    }
    COMPARE_OPERATIONS = {
        "=": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        ">": operator.gt,
        "<=": operator.le,
        ">=": operator.ge,
    }
    COMPARE_FUNCTIONS = {
        "in": "isin",
        "not in": "notin",
        "contains": "like",
        "ends with": "like",
        "starts with": "like",
        "not contains": "not_like",
    }
    NULL_COMPARE_OPERATIONS = {
        "is set": "isnotnull",
        "is not set": "isnull",
    }
    RANGE_OPERATORS = {
        "between": "between",
        "timespan": "between",
    }

    @classmethod
    def get_operation(cls, operator):
        """
        if `operator` = 'like'
        returns a callable method which takes two arguments,
        def anonymous_func(field, value):
            return field.like(value)
        """
        if operator in cls.ARITHMETIC_OPERATIONS:
            return cls.ARITHMETIC_OPERATIONS[operator]

        if operator in cls.COMPARE_OPERATIONS:
            return cls.COMPARE_OPERATIONS[operator]

        if operator in cls.COMPARE_FUNCTIONS:
            function_name = cls.COMPARE_FUNCTIONS[operator]
            return lambda field, value: getattr(field, function_name)(value)

        if operator in cls.RANGE_OPERATORS:
            function_name = cls.RANGE_OPERATORS[operator]
            return lambda field, value: getattr(field, function_name)(
                value[0], value[1]
            )

        if operator == "is":
            return lambda field, value: getattr(
                field, cls.NULL_COMPARE_OPERATIONS[f"{operator} {value}"]
            )()

        raise NotImplementedError(f"Operation {operator} not implemented")


def get_date_range(
    timespan: str, n: int = 1
) -> Tuple[datetime.datetime, datetime.datetime]:

    today = nowdate()

    date_range_map = {
        "current day": lambda: (
            today,
            today,
        ),
        "current week": lambda: (
            get_first_day_of_week(today),
            get_last_day_of_week(today),
        ),
        "current month": lambda: (
            get_first_day(today),
            get_last_day(today),
        ),
        "current quarter": lambda: (
            get_quarter_start(today),
            get_quarter_ending(today),
        ),
        "current year": lambda: (
            get_year_start(today),
            get_year_ending(today),
        ),
        "last n days": lambda n: (
            add_to_date(today, days=-1 * n),
            add_to_date(today, days=-1 * n),
        ),
        "last n weeks": lambda n: (
            get_first_day_of_week(add_to_date(today, days=-7 * n)),
            get_last_day_of_week(add_to_date(today, days=-7 * n)),
        ),
        "last n months": lambda n: (
            get_first_day(add_to_date(today, months=-1 * n)),
            get_last_day(add_to_date(today, months=-1 * n)),
        ),
        "last n quarters": lambda n: (
            get_quarter_start(add_to_date(today, months=-3 * n)),
            get_quarter_ending(add_to_date(today, months=-3 * n)),
        ),
        "last n years": lambda n: (
            get_year_start(add_to_date(today, years=-1 * n)),
            get_year_ending(add_to_date(today, years=-1 * n)),
        ),
    }

    if timespan in date_range_map:
        return (
            date_range_map[timespan]()
            if "current" in timespan
            else date_range_map[timespan](n)
        )


class Functions:
    @classmethod
    def get_functions(cls):
        return {
            "abs": fn.Abs,
            "case": cls.case,
            "floor": fn.Floor,
            "lower": fn.Lower,
            "upper": fn.Upper,
            "concat": fn.Concat,
            "isnull": fn.IsNull,
            "ifnull": fn.IfNull,
            "coalesce": fn.Coalesce,
            "between": cls.between,
            "contains": cls.contains,
            "endswith": cls.endswith,
            "startswith": cls.startswith,
            "ceil": CustomFunction("CEIL", ["field"]),
            "round": CustomFunction("ROUND", ["field"]),
            "replace": CustomFunction("REPLACE", ["field", "find", "replace"]),
        }

    @classmethod
    def get_function(cls, function):
        return cls.get_functions()[function]

    @classmethod
    def contains(cls, field: Field, value):
        return field.like(f"%{value}%")

    @classmethod
    def endswith(cls, field: Field, value):
        return field.like(f"%{value}")

    @classmethod
    def startswith(cls, field: Field, value):
        return field.like(f"{value}%")

    @classmethod
    def between(cls, field: Field, *values):
        return field.between(*values)

    @classmethod
    def ifelse(cls, condition, true_value, false_value):
        return Case().when(condition, true_value).else_(false_value)

    @classmethod
    def case(cls, *args):
        # TODO: validate args at a better place
        _args = list(args)
        if len(_args) % 2 == 0:
            frappe.throw("Case requires an odd number of arguments")

        case = Case()
        default = _args.pop()
        conditions = _args[::2]
        values = _args[1::2]
        for condition, value in zip(conditions, values):
            case.when(condition, value)
        return case.else_(default)

    @classmethod
    def is_valid(cls, function: str):
        return function in cls.get_functions()

    @classmethod
    def apply(cls, function, *args):
        return cls.get_function(function)(*args)


def parse_query_expression(expression):
    expression = _dict(expression)

    if expression.type == "BinaryExpression":
        left = parse_query_expression(expression.left)
        right = parse_query_expression(expression.right)
        operator = expression.operator
        operation = Operations.get_operation(operator)
        return operation(left, right)

    if expression.type == "FunctionCall":
        function = expression.function
        arguments = [parse_query_expression(arg) for arg in expression.arguments]
        if Aggregations.is_valid(function):
            return Aggregations.apply(function, *arguments)
        if Functions.is_valid(function):
            return Functions.apply(function, *arguments)

        raise NotImplementedError(f"Function {function} not implemented")

    if expression.type == "Column":
        column = make_query_field(
            expression.value.get("table"), expression.value.get("column")
        )
        return column

    if expression.type == "String":
        return expression.value

    if expression.type == "Number":
        return expression.value

    frappe.throw("Invalid expression type: {}".format(expression.type))


def make_query_field(table, column) -> Field:
    return Table(table)[column]
