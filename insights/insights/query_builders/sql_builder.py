import operator
from contextlib import suppress
from functools import reduce

from frappe import _dict, parse_json
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
from sqlalchemy import Column, column, table
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Query
from sqlalchemy.sql import and_, case, func, or_

from insights.insights.doctype.insights_query.insights_query import InsightsQuery


class Aggregations:
    @classmethod
    def apply(cls, aggregation, column=None, conditions=None, **kwargs):
        if not aggregation:
            return column
        if aggregation == "Group By":
            return column

        agg_lower = aggregation.lower()
        if agg_lower == "sum":
            return func.sum(column)
        if agg_lower == "min":
            return func.min(column)
        if agg_lower == "max":
            return func.max(column)
        if agg_lower == "avg":
            return func.avg(column)
        if agg_lower == "count":
            return func.count("*")
        if agg_lower == "sum_if":
            return func.sum(case([(conditions, column)], else_=0))
        if agg_lower == "count_if":
            return func.sum(case([(conditions, 1)], else_=0))
        if agg_lower == "distinct":
            return func.distinct(column)

        raise NotImplementedError(f"Aggregation {aggregation} not implemented")


class ColumnFormatter:
    @classmethod
    def format(cls, format_option: dict, column_type: str, column: Column) -> Column:
        if format_option and column_type in ("Date", "Datetime"):
            return cls.format_date(format_option.date_format, column)
        return column

    @classmethod
    def format_date(cls, format, column: Column):
        if format == "Minute":
            return func.date_format(column, "%Y-%m-%d %H:%M")
        if format == "Hour":
            return func.date_format(column, "%Y-%m-%d %H:00")
        if format == "Day" or format == "Day Short":
            return func.date_format(column, "%Y-%m-%d")
        if format == "Month" or format == "Mon":
            return func.date_format(column, "%Y-%m-01")
        if format == "Year":
            return func.date_format(column, "%Y-01-01")
        if format == "Minute of Hour":
            return func.date_format(column, "00:%M")
        if format == "Hour of Day":
            return func.date_format(column, "%H:00")
        if format == "Day of Week":
            return func.date_format(column, "%w")
        if format == "Day of Month":
            return func.date_format(column, "%d")
        if format == "Day of Year":
            return func.date_format(column, "%j")
        if format == "Month of Year":
            return func.date_format(column, "%m")
        if format == "Quarter of Year":
            return func.quarter(column)
        if format == "Quarter":
            return func.str_to_date(
                func.concat(
                    func.year(column),  # 2018
                    "-",  # 2018-
                    (func.quarter(column) * 3) - 2,  # 2018-4
                    "-01",  # 2018-4-01
                ),
                "%Y-%m-%d",
            )


class Functions:
    @classmethod
    def apply(cls, function, *args):
        if function == "abs":
            return func.abs(args[0])

        if function == "now":
            return func.now()

        if function == "in":
            return args[0].in_(args[1])

        if function == "today":
            return func.date(func.now())

        if function == "not_in":
            return args[0].notin_(args[1])

        if function == "floor":
            return func.floor(args[0])

        if function == "lower":
            return func.lower(args[0])

        if function == "upper":
            return func.upper(args[0])

        if function == "concat":
            return func.concat(*args)

        if function == "is_set":
            return args[0].isnot(None)

        if function == "is_not_set":
            return args[0].is_(None)

        if function == "if_null":
            return func.ifnull(args[0], args[1])

        if function == "coalesce":
            return func.coalesce(*args)

        if function == "between":
            return args[0].between(args[1], args[2])

        if function == "contains":
            return args[0].like("%" + args[1] + "%")

        if function == "not_contains":
            return ~args[0].like("%" + args[1] + "%")

        if function == "ends_with":
            return args[0].like("%" + args[1])

        if function == "starts_with":
            return args[0].like(args[1] + "%")

        if function == "ceil":
            return func.ceil(args[0])

        if function == "round":
            return func.round(args[0])

        if function == "replace":
            return func.replace(args[0], args[1], args[2])

        if function == "case":
            _args = list(args)
            if len(_args) % 2 == 0:
                raise Exception("Case function requires an odd number of arguments")
            default = _args.pop()
            conditions = []
            for i in range(0, len(_args), 2):
                conditions.append((_args[i], _args[i + 1]))
            return case(conditions, else_=default)

        if function == "timespan":
            timespan = args[0].lower().strip()
            if "current" not in timespan or "last" not in timespan:
                raise Exception(f"Invalid timespan: {timespan}")

            if "current" in timespan:
                date_range = get_date_range(timespan)
            elif "last" in timespan:
                [span, interval, interval_type] = timespan.split(" ")
                timespan = span + " n " + interval_type
                date_range = get_date_range(timespan, n=int(interval))
            return args[1].between(date_range[0], date_range[1])

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
            return func.timestampdiff(unit, args[1], args[2])

        raise NotImplementedError(f"Function {function} not implemented")


def get_date_range(timespan: str, n: int = 1):
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
        "&&": lambda a, b: and_(a, b),
        "||": lambda a, b: or_(a, b),
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


class ExpressionProcessor:
    @classmethod
    def process(cls, expression, query: InsightsQuery = None):
        expression = _dict(expression)
        cls.query = query if query else cls.query

        if expression.type == "LogicalExpression":
            return cls.process_logical_expression(expression)

        if expression.type == "BinaryExpression":
            return cls.process_binary_expression(expression)

        if expression.type == "CallExpression":
            return cls.process_call_expression(expression)

        if expression.type == "Column":
            column = expression.value.get("column")
            table = expression.value.get("table")
            return cls.query.find_or_add_column(column, table)

        if expression.type == "String":
            return expression.value

        if expression.type == "Number":
            return expression.value

        raise NotImplementedError(f"Invalid expression type: {expression.type}")

    @classmethod
    def process_logical_expression(cls, expression):
        conditions = []
        GroupCriteria = and_ if expression.operator == "&&" else or_
        for condition in expression.get("conditions"):
            condition = _dict(condition)
            conditions.append(cls.process(condition))
        return GroupCriteria(*conditions if conditions else [True])

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
            return Aggregations.apply(function, *arguments)

        raise NotImplementedError(f"Function {function} not implemented")


class SQLQueryBuilder:
    column_formatter = ColumnFormatter

    def build(self, query: InsightsQuery, dialect: Dialect = None):
        self.query = query
        self.dialect = dialect
        self.process_tables()
        self.process_joins()
        self.process_columns()
        self.process_filters()
        return self.make_query()

    def process_tables(self):
        self._tables = []
        for row in self.query.tables:
            table = self.find_or_add_table(row.table)
            if table not in self._tables:
                self._tables.append(table)

    def find_or_add_table(self, name):
        return next((t for t in self._tables if t.name == name), table(name))

    def find_or_add_column(self, name, table):
        _table = self.find_or_add_table(table)
        if name not in _table.c:
            _table.append_column(column(name))
        return _table.c[name]

    def process_joins(self):
        self._joins = []
        for row in self.query.tables:
            if not row.join:
                continue

            _join = parse_json(row.join)
            join_type = _join.get("type").get("value")

            left_table = self.find_or_add_table(row.table)
            right_table = self.find_or_add_table(_join.get("with").get("value"))

            condition = _join.get("condition").get("value")
            left_key = condition.split("=")[0].strip()
            right_key = condition.split("=")[1].strip()

            left_key = self.find_or_add_column(left_key, row.table)
            right_key = self.find_or_add_column(
                right_key, _join.get("with").get("value")
            )

            self._joins.append(
                _dict(
                    {
                        "left": left_table,
                        "right": right_table,
                        "type": join_type,
                        "left_key": left_key,
                        "right_key": right_key,
                    }
                )
            )

    def process_columns(self):
        self._columns = []
        self._group_by_columns = []
        self._order_by_columns = []

        for row in self.query.columns:
            if not row.is_expression:
                _column = self.find_or_add_column(row.column, row.table)
                _column = self.column_formatter.format(
                    parse_json(row.format_option), row.type, _column
                )
                _column = Aggregations.apply(row.aggregation, _column)
            else:
                expression = parse_json(row.expression)
                _column = ExpressionProcessor.process(expression.get("ast"))
                _column = self.column_formatter.format(
                    parse_json(row.format_option), row.type, _column
                )

            if row.order_by:
                self._order_by_columns.append(
                    _column.asc() if row.order_by == "asc" else _column.desc()
                )

            _column = _column.label(row.label) if row.label else _column

            if row.aggregation == "Group By":
                self._group_by_columns.append(_column)

            self._columns.append(_column)

    def process_filters(self):
        filters = parse_json(self.query.filters)
        self._filters = ExpressionProcessor.process(filters, self)

    def make_query(self):
        query = Query(self._tables)

        if self._joins:
            for _table in self._tables:
                joins = [d for d in self._joins if d.left == _table]
                for join in joins:
                    if join.type == "inner":
                        query = query.select_entity_from(join.left).join(
                            join.right, join.left_key == join.right_key
                        )
                    elif join.type == "left":
                        query = query.select_entity_from(join.left).join(
                            join.right, join.left_key == join.right_key, isouter=True
                        )
                    elif join.type == "right":
                        query = query.select_entity_from(join.right).join(
                            join.left, join.right_key == join.left_key, isouter=True
                        )
                    elif join.type == "full":
                        query = query.select_entity_from(join.left).join(
                            join.right, join.left_key == join.right_key, full=True
                        )

        if not self._columns and self._tables:
            # if no columns, then display all columns
            query = query.with_entities(column("*"))
        if self._columns:
            query = query.with_entities(*self._columns)
        if self._group_by_columns:
            query = query.group_by(*self._group_by_columns)
        if self._order_by_columns:
            query = query.order_by(*self._order_by_columns)
        if self._filters is not None:
            query = query.filter(self._filters)

        return self.compiled(query)

    def compiled(self, query):
        compile_args = {"compile_kwargs": {"literal_binds": True}}
        if self.dialect:
            compile_args["dialect"] = self.dialect
        compiled = query.statement.compile(**compile_args)
        return str(compiled)
