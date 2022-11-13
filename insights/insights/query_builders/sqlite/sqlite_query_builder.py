# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from sqlalchemy import Column
from sqlalchemy.sql import func
from ..sql_builder import SQLQueryBuilder


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


class SQLiteQueryBuilder(SQLQueryBuilder):
    column_formatter = SQLiteColumnFormatter
