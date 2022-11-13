# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import datetime
import operator
from contextlib import suppress
from typing import Tuple

import frappe
from frappe import _dict
from frappe.query_builder import Case, CustomFunction, Field, functions
from frappe.utils.data import (
    add_to_date,
    get_first_day,
    get_first_day_of_week,
    get_last_day,
    get_last_day_of_week,
    get_quarter_ending,
    get_quarter_start,
    get_year_ending,
    get_year_start,
    nowdate,
)
from pypika import Column, Criterion, Query
from pypika import functions as fn


class Aggregations:
    @classmethod
    def get_aggregations(cls):
        return {
            "sum": functions.Sum,
            "min": functions.Min,
            "max": functions.Max,
            "avg": functions.Avg,
            "count": cls.count,
            "sum_if": cls.sum_if,
            "count_if": cls.count_if,
            "distinct": CustomFunction("DISTINCT", ["column"]),
        }

    @classmethod
    def get_aggregation_function(cls, aggregation):
        if aggregation in cls.get_aggregations():
            return cls.get_aggregations()[aggregation]

    @staticmethod
    def count(column):
        if "*" in column.get_sql():
            return functions.Count("*")
        return functions.Count(column)

    @staticmethod
    def sum_if(conditions, column):
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
        # Valid Dates
        "Minute": "%Y-%m-%d %H:%i",  # eg. 2021-01-10 13:21
        "Hour": "%Y-%m-%d %H:00",  # eg. 2021-01-10 13:00
        "Day": "%Y-%m-%d",  # eg. 2021-01-10
        "Month": "%Y-%m-01",  # eg. 2021-01-01
        "Year": "%Y-01-01",  # eg. 2021-01-01
        "Minute of Hour": "00:%i",  # eg. 00:21
        "Hour of Day": "%H:00",  # eg. 13:00
        "Day of Week": "%w",  # eg. 1
        "Day of Month": "%d",  # eg. 01
        "Day of Year": "%j",  # eg. 001
        "Month of Year": "%m",  # eg. 01
    }

    FormatDate = CustomFunction("DATE_FORMAT", ["date", "format"])
    ParseDate = CustomFunction("STR_TO_DATE", ["str", "format"])
    Quarter = CustomFunction("QUARTER", ["date"])

    @classmethod
    def format_date(cls, format, column):
        if format in cls.date_formats:
            _format = cls.date_formats[format]
            return cls.FormatDate(column, _format)
        elif format == "Quarter of Year":
            return cls.Quarter(column)
        elif format == "Quarter":
            # converts any date to the first day of the quarter
            Year = CustomFunction("YEAR", ["date"])
            return cls.ParseDate(
                fn.Concat(Year(column), "-", (cls.Quarter(column) * 3) - 2, "-01"),
                "%Y-%m-%d",
            )

        return column

    @classmethod
    def parse_date(cls, format, column):
        if format in cls.date_formats:
            _format = cls.date_formats[format]
            return cls.ParseDate(column, _format)

        return column


class BinaryOperations:
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
    LOGICAL_OPERATIONS = {
        "&&": lambda a, b: Criterion.all([a, b]),
        "||": lambda a, b: Criterion.any([a, b]),
    }

    @classmethod
    def get_operation(cls, operator):
        if operator in cls.ARITHMETIC_OPERATIONS:
            return cls.ARITHMETIC_OPERATIONS[operator]

        if operator in cls.COMPARE_OPERATIONS:
            return cls.COMPARE_OPERATIONS[operator]

        if operator in cls.LOGICAL_OPERATIONS:
            return cls.LOGICAL_OPERATIONS[operator]

        raise NotImplementedError(f"Operation {operator} not implemented")


class Functions:
    @classmethod
    def get_functions(cls):
        return {
            "abs": fn.Abs,
            "now": fn.Now,
            "in": cls.isin,
            "today": cls.today,
            "not_in": cls.isnotin,
            "case": cls.case,
            "floor": fn.Floor,
            "lower": fn.Lower,
            "upper": fn.Upper,
            "concat": fn.Concat,
            "is_set": cls.isnotnull,
            "is_not_set": fn.IsNull,
            "if_null": fn.IfNull,
            "coalesce": fn.Coalesce,
            "between": cls.between,
            "timespan": cls.timespan,
            "contains": cls.contains,
            "not_contains": cls.not_contains,
            "ends_with": cls.endswith,
            "starts_with": cls.startswith,
            "time_elapsed": cls.time_elapsed,
            "ceil": CustomFunction("CEIL", ["field"]),
            "round": CustomFunction("ROUND", ["field"]),
            "replace": CustomFunction("REPLACE", ["field", "find", "replace"]),
        }

    @classmethod
    def get_function(cls, function):
        return cls.get_functions()[function]

    @staticmethod
    def today():
        return CustomFunction("CURDATE", [])()

    @staticmethod
    def isin(field: Field, *values):
        return field.isin(values)

    @staticmethod
    def isnotin(field: Field, *values):
        return field.notin(values)

    @staticmethod
    def isnotnull(field: Field):
        return field.isnotnull()

    @staticmethod
    def contains(field: Field, value):
        return field.like(f"%{value}%")

    @staticmethod
    def not_contains(field: Field, value):
        return field.not_like(f"%{value}%")

    @staticmethod
    def endswith(field: Field, value):
        return field.like(f"%{value}")

    @staticmethod
    def startswith(field: Field, value):
        return field.like(f"{value}%")

    @staticmethod
    def between(field: Field, *values):
        return field.between(*values)

    @staticmethod
    def timespan(field: Field, timespan: str):
        timespan = timespan.lower().strip()
        if "current" in timespan:
            date_range = get_date_range(timespan=timespan)

        elif "last" in timespan:
            [span, interval, interval_type] = timespan.split(" ")
            timespan = span + " n " + interval_type
            date_range = get_date_range(timespan=timespan, n=int(interval))
        return field.between(date_range[0], date_range[1])

    @staticmethod
    def ifelse(condition, true_value, false_value):
        return Case().when(condition, true_value).else_(false_value)

    @staticmethod
    def case(*args):
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

    @staticmethod
    def time_elapsed(unit, start_date, end_date):
        from pypika.terms import LiteralValue

        VALID_UNITS = [
            "MICROSECOND",
            "SECOND",
            "MINUTE",
            "HOUR",
            "DAY",
            "WEEK",
            "MONTH",
            "QUARTER",
            "YEAR",
        ]
        if unit.upper() not in VALID_UNITS:
            frappe.throw(
                f"Invalid unit {unit}. Valid units are {', '.join(VALID_UNITS)}"
            )

        timestamp_diff = CustomFunction(
            "TIMESTAMPDIFF", ["unit", "start_date", "end_date"]
        )
        unit = LiteralValue(unit.upper())
        return timestamp_diff(unit, start_date, end_date)

    @classmethod
    def is_valid(cls, function: str):
        return function in cls.get_functions()

    @classmethod
    def apply(cls, function, *args):
        if cls.is_valid(function):
            return cls.get_function(function)(*args)
        raise NotImplementedError(f"Function {function} not implemented")


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
            add_to_date(today, days=-1),
        ),
        "last n weeks": lambda n: (
            get_first_day_of_week(add_to_date(today, days=-7 * n)),
            get_last_day_of_week(add_to_date(today, days=-7)),
        ),
        "last n months": lambda n: (
            get_first_day(add_to_date(today, months=-1 * n)),
            get_last_day(add_to_date(today, months=-1)),
        ),
        "last n quarters": lambda n: (
            get_quarter_start(add_to_date(today, months=-3 * n)),
            get_quarter_ending(add_to_date(today, months=-3)),
        ),
        "last n years": lambda n: (
            get_year_start(add_to_date(today, years=-1 * n)),
            get_year_ending(add_to_date(today, years=-1)),
        ),
    }

    if timespan in date_range_map:
        return (
            date_range_map[timespan]()
            if "current" in timespan
            else date_range_map[timespan](n)
        )


class ColumnProcessor:
    query_cls = Query
    aggregations = Aggregations
    formatter = ColumnFormat

    @classmethod
    def make_column(cls, column: str, table: str):
        return cls.query_cls.Table(table)[column]

    @classmethod
    def process_aggregation(cls, aggregation: str, column: Column) -> Column:
        if not aggregation or aggregation.lower() == "group by":
            return column
        else:
            return cls.aggregations.apply(aggregation.lower(), column)

    @classmethod
    def process_format(
        cls, format_option: dict, column_type: str, column: Column
    ) -> Column:
        if format_option and column_type in ("Date", "Datetime"):
            return cls.formatter.format_date(format_option.date_format, column)
        return column

    @classmethod
    def parse_date(cls, format_option: dict, column: Column) -> Column:
        return cls.formatter.parse_date(format_option.date_format, column)


class ExpressionProcessor:
    column_processor = ColumnProcessor

    @classmethod
    def process(cls, expression):
        expression = _dict(expression)

        if expression.type == "LogicalExpression":
            return cls.process_logical_expression(expression)

        if expression.type == "BinaryExpression":
            return cls.process_binary_expression(expression)

        if expression.type == "CallExpression":
            return cls.process_call_expression(expression)

        if expression.type == "Column":
            return cls.column_processor.make_column(
                expression.value.get("column"),
                expression.value.get("table"),
            )

        if expression.type == "String":
            return expression.value

        if expression.type == "Number":
            return expression.value

        frappe.throw("Invalid expression type: {}".format(expression.type))

    @classmethod
    def process_logical_expression(cls, expression):
        conditions = []
        GroupCriteria = Criterion.all if expression.operator == "&&" else Criterion.any
        for condition in expression.get("conditions"):
            condition = _dict(condition)
            conditions.append(cls.process(condition))
        return GroupCriteria(conditions)

    @classmethod
    def process_binary_expression(cls, expression):
        left = cls.process(expression.left)
        right = cls.process(expression.right)
        operator = expression.operator
        operation = BinaryOperations.get_operation(operator)
        return operation(left, right)

    @classmethod
    def process_call_expression(cls, expression):
        function = expression.function
        arguments = [cls.process(arg) for arg in expression.arguments]

        with suppress(NotImplementedError):
            return Functions.apply(function, *arguments)

        with suppress(NotImplementedError):
            return cls.column_processor.aggregations.apply(function, *arguments)

        raise NotImplementedError(f"Function {function} not implemented")
