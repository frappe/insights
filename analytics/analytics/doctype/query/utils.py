# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import operator

from frappe.query_builder import CustomFunction, functions, Case


class Aggregations:

    functions = {
        "Sum": functions.Sum,
        "Count": functions.Count,
        "Min": functions.Min,
        "Max": functions.Max,
        "Avg": functions.Avg,
        "Distinct": CustomFunction("DISTINCT", ["column"]),
    }

    @classmethod
    def apply(cls, aggregation, column=None, **kwargs):
        if aggregation == "Count if":
            conditions = kwargs.get("conditions")
            return functions.Sum(Case().when(conditions, 1).else_(0))
        if aggregation in cls.functions:
            return cls.functions[aggregation](column)


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
