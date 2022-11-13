# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from sqlalchemy import Column
from sqlalchemy.sql import func

from ..sql_builder import Functions, SQLQueryBuilder


class SQLiteColumnFormatter:
    @classmethod
    def format(cls, format_option: dict, column_type: str, column: Column) -> Column:
        if format_option and column_type in ("Date", "Datetime"):
            return cls.format_date(format_option.date_format, column)
        return column

    @classmethod
    def format_date(cls, format, column: Column):
        if format == "Minute":
            return func.strftime("%Y-%m-%d %H:%M", column)
        if format == "Hour":
            return func.strftime("%Y-%m-%d %H:00", column)
        if format == "Day" or format == "Day Short":
            return func.strftime("%Y-%m-%d", column)
        if format == "Month" or format == "Mon":
            return func.strftime("%Y-%m-01", column)
        if format == "Year":
            return func.strftime("%Y-01-01", column)
        if format == "Minute of Hour":
            return func.strftime("00:%M", column)
        if format == "Hour of Day":
            return func.strftime("%H:00", column)
        if format == "Day of Week":
            return func.strftime("%w", column)
        if format == "Day of Month":
            return func.strftime("%d", column)
        if format == "Day of Year":
            return func.strftime("%j", column)
        if format == "Month of Year":
            return func.strftime("%m", column)

        if format == "Quarter of Year":
            month = func.strftime("%m", column)
            return (month - 1) / 3

        if format == "Quarter":
            date = func.strftime("%Y-%m-01", column)
            month = func.strftime("%m", column)
            # DATE(date, ('-' || (month - 1) % 3 || ' months'))
            return func.date(
                date,
                ("-" + func.mod((month - 1), 3) + " months"),
            )

        return column


class SQLiteFunctions(Functions):
    @classmethod
    def apply(cls, function, *args):

        if function == "concat":
            from functools import reduce

            return reduce(lambda x, y: x + y, args)

        if function == "time_elapsed":
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
            unit = args[0].upper()
            if unit not in VALID_UNITS:
                raise Exception(
                    f"Invalid unit {unit}. Valid units are {', '.join(VALID_UNITS)}"
                )

            day_diff = func.julianday(args[1]) - func.julianday(args[2])

            if unit == "MICROSECOND":
                return day_diff * 86400000000
            if unit == "SECOND":
                return day_diff * 86400
            if unit == "MINUTE":
                return day_diff * 1440
            if unit == "HOUR":
                return day_diff * 24
            if unit == "DAY":
                return day_diff
            if unit == "WEEK":
                return day_diff / 7
            if unit == "MONTH":
                return day_diff / 30
            if unit == "QUARTER":
                return day_diff / 90
            if unit == "YEAR":
                return day_diff / 365

        return super().apply(function, *args)


class SQLiteQueryBuilder(SQLQueryBuilder):
    column_formatter = SQLiteColumnFormatter
    functions = SQLiteFunctions
