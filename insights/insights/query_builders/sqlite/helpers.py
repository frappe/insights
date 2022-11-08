# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from pypika.terms import LiteralValue, Function
from ..pypika.helpers import ColumnProcessor, ExpressionProcessor
from pypika import SQLLiteQuery, Column, CustomFunction, Case, functions as fn


class SQLiteColumnFormat:
    @classmethod
    def format_date(cls, format, column: Column):
        STRFTIME = CustomFunction("STRFTIME", ["format", "date"])
        if format == "Minute":
            return STRFTIME("%Y-%m-%d %H:%M", column)
        if format == "Hour":
            return STRFTIME("%Y-%m-%d %H:00", column)
        if format == "Day" or format == "Day Short":
            return STRFTIME("%Y-%m-%d", column)
        if format == "Month" or format == "Mon":
            return STRFTIME("%Y-%m-01", column)
        if format == "Year":
            return STRFTIME("%Y-01-01", column)
        if format == "Minute of Hour":
            return STRFTIME("00:%M", column)
        if format == "Hour of Day":
            return STRFTIME("%H:00", column)
        if format == "Day of Week":
            return STRFTIME("%w", column)
        if format == "Day of Month":
            return STRFTIME("%d", column)
        if format == "Day of Year":
            return STRFTIME("%j", column)
        if format == "Month of Year":
            return STRFTIME("%m", column)

        if format == "Quarter of Year":
            month = STRFTIME("%m", column)
            return (month - LiteralValue("1")) / LiteralValue("3")

        if format == "Quarter":

            def concat(*args):
                return LiteralValue(" || ".join(str(arg) for arg in args))

            date = STRFTIME("%Y-%m-01", column)
            month = STRFTIME("%m", column)
            # DATE(date, ('-' || (month - 1) % 3 || ' months'))
            return Function(
                "DATE",
                date,
                concat(
                    LiteralValue("'-'"),
                    (month - LiteralValue("1")) % LiteralValue("3"),
                    LiteralValue("' months'"),
                ),
            )

        return column


class SQLiteAggregations:
    @classmethod
    def apply(cls, aggregation, column=None, conditions=None, **kwargs):
        if aggregation == "sum":
            return fn.Sum(column)
        if aggregation == "min":
            return fn.Min(column)
        if aggregation == "max":
            return fn.Max(column)
        if aggregation == "avg":
            return fn.Avg(column)
        if aggregation == "count":
            return fn.Count("*")
        if aggregation == "sum_if":
            return fn.Sum(Case().when(conditions, column).else_(0))
        if aggregation == "count_if":
            return fn.Sum(Case().when(column, 1).else_(0))
        if aggregation == "distinct":
            return Function("DISTINCT", column)

        raise NotImplementedError(f"Aggregation {aggregation} not implemented")


class SQLiteColumnProcessor(ColumnProcessor):
    query_cls = SQLLiteQuery
    aggregations = SQLiteAggregations
    formatter = SQLiteColumnFormat


class SQLiteExpressionProcessor(ExpressionProcessor):
    column_processor = SQLiteColumnProcessor
