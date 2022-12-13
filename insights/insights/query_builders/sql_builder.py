import operator
from contextlib import suppress

from frappe import _dict, parse_json
from frappe.utils.data import (
    add_to_date,
    get_date_str,
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
from sqlalchemy import Column
from sqlalchemy import column as sa_column
from sqlalchemy import select, table
from sqlalchemy.engine import Dialect
from sqlalchemy.sql import and_, case, distinct, func, or_, text


class Aggregations:
    @classmethod
    def apply(cls, aggregation: str, column=None):
        if not aggregation:
            return column
        if aggregation == "Group By":
            return column

        agg_lower = aggregation.lower()
        if agg_lower == "sum" or agg_lower == "cumulative sum":
            return func.sum(column)
        if agg_lower == "min":
            return func.min(column)
        if agg_lower == "max":
            return func.max(column)
        if agg_lower == "avg":
            return func.avg(column)
        if agg_lower == "count" or agg_lower == "cumulative count":
            return func.count(text("*"))

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


def get_descendants(node, tree, include_self=False):
    Tree = table(tree, sa_column("lft"), sa_column("rgt"), sa_column("name"))
    lft_rgt = (
        select([Tree.c.lft, Tree.c.rgt]).where(Tree.c.name == node).alias("lft_rgt")
    )
    return (
        (
            select([Tree.c.name])
            .where(Tree.c.lft > lft_rgt.c.lft)
            .where(Tree.c.rgt < lft_rgt.c.rgt)
            .order_by(Tree.c.lft.asc())
        )
        if not include_self
        else (
            select([Tree.c.name])
            .where(Tree.c.lft >= lft_rgt.c.lft)
            .where(Tree.c.rgt <= lft_rgt.c.rgt)
            .order_by(Tree.c.lft.asc())
        )
    )


class Functions:
    @classmethod
    def apply(cls, function, *args):

        # no args functions

        if function == "now":
            return func.now()

        if function == "today":
            return func.date(func.now())

        # single arg functions

        if function == "abs":
            return func.abs(args[0])

        if function == "floor":
            return func.floor(args[0])

        if function == "lower":
            return func.lower(args[0])

        if function == "upper":
            return func.upper(args[0])

        if function == "ceil":
            return func.ceil(args[0])

        if function == "round":
            return func.round(args[0])

        if function == "is_set":
            return args[0].isnot(None)

        if function == "is_not_set":
            return args[0].is_(None)

        if function == "count_if":
            return func.sum(case([(args[0], 1)], else_=0))

        if function == "distinct":
            return distinct(args[0])

        if function == "distinct_count":
            return func.count(distinct(args[0]))

        # two arg functions

        if function == "in":
            # args = [column, value1, value2, ...]
            return args[0].in_(args[1:])

        if function == "not_in":
            # args = [column, value1, value2, ...]
            return args[0].notin_(args[1:])

        if function == "contains":
            return args[0].like("%" + args[1] + "%")

        if function == "not_contains":
            return ~args[0].like("%" + args[1] + "%")

        if function == "ends_with":
            return args[0].like("%" + args[1])

        if function == "starts_with":
            return args[0].like(args[1] + "%")

        if function == "if_null":
            return func.ifnull(args[0], args[1])

        if function == "sum_if":
            return func.sum(case([(args[0], args[1])], else_=0))

        # three arg functions

        if function == "between":
            return args[0].between(args[1], args[2])

        if function == "replace":
            return func.replace(args[0], args[1], args[2])

        if function == "concat":
            return func.concat(*args)

        if function == "coalesce":
            return func.coalesce(*args)

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
            column = args[0]
            timespan = args[1].lower()
            timespan = timespan[:-1] if timespan.endswith("s") else timespan

            units = ["day", "week", "month", "quarter", "year"]
            unit = timespan.split(" ")[-1]
            if unit not in units:
                raise Exception(f"Invalid timespan unit {unit}")

            dates = get_date_range(timespan)
            if not dates:
                raise Exception(f"Invalid timespan {args[1]}")

            return column.between(get_date_str(dates[0]), get_date_str(dates[1]))

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
            return func.timestampdiff(text(unit), args[1], args[2])

        if function == "descendants":
            node = args[0]  # "India"
            tree = args[1]  # "territory"
            field = args[2]  # salesorder.territory
            query = get_descendants(node, tree, include_self=False)
            return field.in_(query)

        if function == "descendants_and_self":
            node = args[0]  # "India"
            tree = args[1]  # "territory"
            field = args[2]  # salesorder.territory
            query = get_descendants(node, tree, include_self=True)
            return field.in_(query)

        raise NotImplementedError(f"Function {function} not implemented")


def get_current_date_range(unit):
    today = nowdate()
    if unit == "day":
        return [today, today]
    if unit == "week":
        return [get_first_day_of_week(today), get_last_day_of_week(today)]
    if unit == "month":
        return [get_first_day(today), get_last_day(today)]
    if unit == "quarter":
        return [get_quarter_start(today), get_quarter_ending(today)]
    if unit == "year":
        return [get_year_start(today), get_year_ending(today)]


def get_directional_date_range(direction, unit, number_of_unit):
    dates = []
    today = nowdate()
    if unit == "day":
        dates = [
            add_to_date(today, days=direction * number_of_unit),
            add_to_date(today, days=direction),
        ]
    if unit == "week":
        dates = [
            get_first_day_of_week(
                add_to_date(today, days=direction * 7 * number_of_unit)
            ),
            get_last_day_of_week(add_to_date(today, days=direction * 7)),
        ]
    if unit == "month":
        dates = [
            get_first_day(add_to_date(today, months=direction * number_of_unit)),
            get_last_day(add_to_date(today, months=direction)),
        ]
    if unit == "quarter":
        dates = [
            get_quarter_start(
                add_to_date(today, months=direction * 3 * number_of_unit)
            ),
            get_quarter_ending(add_to_date(today, months=direction * 3)),
        ]
    if unit == "year":
        dates = [
            get_year_start(add_to_date(today, years=direction * number_of_unit)),
            get_year_ending(add_to_date(today, years=direction)),
        ]

    if dates[0] > dates[1]:
        dates.reverse()
    return dates


def get_date_range(timespan, include_current=False):
    # timespan = "last 7 days" or "next 3 months"
    direction = timespan.lower().split(" ")[0]  # "last" or "next" or "current"
    unit = timespan.lower().split(" ")[-1]  # "day", "week", "month", "quarter", "year"

    if direction == "current":
        return get_current_date_range(unit)

    number_of_unit = int(timespan.split(" ")[1])  # 7, 3, etc

    if direction == "last" or direction == "next":
        direction = -1 if direction == "last" else 1

        dates = get_directional_date_range(direction, unit, number_of_unit)

        if include_current:
            current_dates = get_current_date_range(unit)
            dates[0] = min(dates[0], current_dates[0])
            dates[1] = max(dates[1], current_dates[1])

        return dates


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
    def __init__(self, builder: "SQLQueryBuilder"):
        self.builder = builder

    def process(self, expression):
        expression = _dict(expression)

        if expression.type == "LogicalExpression":
            return self.process_logical_expression(expression)

        if expression.type == "BinaryExpression":
            return self.process_binary_expression(expression)

        if expression.type == "CallExpression":
            return self.process_call_expression(expression)

        if expression.type == "Column":
            column = expression.value.get("column")
            table = expression.value.get("table")
            return self.builder.make_column(column, table)

        if expression.type == "String":
            return expression.value

        if expression.type == "Number":
            return expression.value

        raise NotImplementedError(f"Invalid expression type: {expression.type}")

    def process_logical_expression(self, expression):
        conditions = []
        GroupCriteria = and_ if expression.operator == "&&" else or_
        for condition in expression.get("conditions"):
            condition = _dict(condition)
            conditions.append(self.process(condition))
        if conditions:
            return GroupCriteria(*conditions)

    def process_binary_expression(self, expression):
        left = self.process(expression.left)
        right = self.process(expression.right)
        operator = expression.operator
        operation = BinaryOperations.get_operation(operator)
        return operation(left, right)

    def process_call_expression(self, expression):
        function = expression.function
        arguments = [self.process(arg) for arg in expression.arguments]

        with suppress(NotImplementedError):
            return self.builder.functions.apply(function, *arguments)

        if len(arguments) <= 2:
            with suppress(NotImplementedError):
                return self.builder.aggregations.apply(function, *arguments)

        raise NotImplementedError(f"Function {function} not implemented")


class SQLQueryBuilder:
    def __init__(self) -> None:
        self.functions = Functions
        self.aggregations = Aggregations
        self.column_formatter = ColumnFormatter
        self.expression_processor = ExpressionProcessor(self)

        self._tables = {}
        self._joins = []
        self._columns = []
        self._filters = []
        self._group_by_columns = []
        self._order_by_columns = []
        self._limit = 500

    def build(self, query, dialect: Dialect = None):
        self.query = query
        self.dialect = dialect
        self.process_tables_and_joins()
        self.process_columns()
        self.process_filters()
        return self.make_query()

    def make_table(self, name):
        if not hasattr(self, "_tables"):
            self._tables = {}
        if name not in self._tables:
            self._tables[name] = table(name).alias(f"t{len(self._tables)}")
        return self._tables[name]

    def make_column(self, columnname, tablename):
        _table = self.make_table(tablename)
        return sa_column(columnname, _selectable=_table)

    def process_tables_and_joins(self):
        self._joins = []
        for row in self.query.tables:
            if not row.join:
                continue

            _join = parse_json(row.join)
            join_type = _join.get("type").get("value")

            left_table = self.make_table(row.table)
            right_table = self.make_table(_join.get("with").get("value"))

            condition = _join.get("condition")
            left_key = condition.get("left").get("value")
            right_key = condition.get("right").get("value")

            left_key = self.make_column(left_key, row.table)
            right_key = self.make_column(right_key, _join.get("with").get("value"))

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
                _column = self.make_column(row.column, row.table)
                _column = self.column_formatter.format(
                    parse_json(row.format_option), row.type, _column
                )
                _column = self.aggregations.apply(row.aggregation, _column)
            else:
                expression = parse_json(row.expression)
                _column = self.expression_processor.process(expression.get("ast"))
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
        self._filters = self.expression_processor.process(filters)

    def make_query(self):
        if not self.query.tables:
            return

        sql = None
        if not self._columns:
            # if no columns, then select * from table
            sql = select(text("*"))
        else:
            sql = select(*self._columns)

        main_table = self.query.tables[0].table
        sql = sql.select_from(self.make_table(main_table))

        if self._joins:
            sql = self.do_join(sql)
        if self._group_by_columns:
            sql = sql.group_by(*self._group_by_columns)
        if self._order_by_columns:
            sql = sql.order_by(*self._order_by_columns)
        if self._filters is not None:
            sql = sql.filter(self._filters)

        sql = sql.limit(self.query.limit or self._limit)

        return self.compile(sql)

    def do_join(self, sql):
        # TODO: add right and full joins

        for join in self._joins:

            sql = sql.join_from(
                join.left,
                join.right,
                join.left_key == join.right_key,
                isouter=join.type == "left",
            )

        return sql

    def compile(self, query):
        compile_args = {"compile_kwargs": {"literal_binds": True}}
        if self.dialect:
            compile_args["dialect"] = self.dialect
        compiled = query.compile(**compile_args)
        return str(compiled)
