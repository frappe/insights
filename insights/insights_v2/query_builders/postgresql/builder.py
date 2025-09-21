from sqlalchemy import Column
from sqlalchemy.sql import func

from ..sql_builder import ColumnFormatter, Functions, SQLQueryBuilder


class PostgresColumnFormatter(ColumnFormatter):
    @classmethod
    def format_date(cls, format, column: Column):
        match format:
            case "Minute":
                return func.to_char(column, "YYYY-MM-DD HH24:MI")
            case "Hour":
                return func.to_char(column, "YYYY-MM-DD HH24:00")
            case "Day" | "Day Short":
                return func.to_char(column, "YYYY-MM-DD 00:00")
            case "Week":
                return func.date_trunc("week", column)
            case "Month" | "Mon":
                return func.to_char(column, "YYYY-MM-01")
            case "Year":
                return func.to_char(column, "YYYY-01-01")
            case "Minute of Hour":
                return func.to_char(column, "00:MI")
            case "Hour of Day":
                return func.to_char(column, "HH:00")
            case "Day of Week":
                return func.to_char(column, "Day")
            case "Day of Month":
                return func.to_char(column, "DD")
            case "Day of Year":
                return func.to_char(column, "DDD")
            case "Month of Year":
                return func.to_char(column, "MM")
            case "Quarter of Year":
                return func.date_part("quarter", column)
            case "Quarter":
                return func.to_date(
                    func.concat(
                        func.extract("year", column),
                        "-",
                        (func.extract("quarter", column) * 3) - 2,
                        "-01",
                    ),
                    "YYYY-MM-DD",
                )
            case _:
                return func.to_char(column, format)


class PostgresQueryBuilder(SQLQueryBuilder):
    def __init__(self, engine):
        super().__init__(engine)
        self.engine = engine
        self.functions = Functions
        self.column_formatter = PostgresColumnFormatter
