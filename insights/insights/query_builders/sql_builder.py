import operator
from contextlib import suppress
from datetime import date, datetime

import frappe
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
    getdate,
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
        if agg_lower == "distinct":
            return distinct(column)
        if agg_lower == "distinct_count":
            return func.count(distinct(column))

        raise NotImplementedError(f"Aggregation {aggregation} not implemented")


class ColumnFormatter:
    @classmethod
    def format(cls, format_options: dict, column_type: str, column: Column) -> Column:
        if format_options and format_options.date_format and column_type in ("Date", "Datetime"):
            date_format = format_options.date_format
            date_format = date_format if type(date_format) == str else date_format.get("value")
            return cls.format_date(date_format, column)
        return column

    @classmethod
    def format_date(cls, format, column: Column):
        if format == "Minute":
            return func.date_format(column, "%Y-%m-%d %H:%i")
        if format == "Hour":
            return func.date_format(column, "%Y-%m-%d %H:00")
        if format == "Day" or format == "Day Short":
            return func.date_format(column, "%Y-%m-%d 00:00")
        if format == "Week":
            # DATE_FORMAT(install_date, '%Y-%m-%d') - INTERVAL (DAYOFWEEK(install_date) - 1) DAY,
            date = func.date_format(column, "%Y-%m-%d")
            return func.DATE_SUB(date, text(f"INTERVAL (DAYOFWEEK({column}) - 1) DAY"))
        if format == "Month" or format == "Mon":
            return func.date_format(column, "%Y-%m-01")
        if format == "Year":
            return func.date_format(column, "%Y-01-01")
        if format == "Minute of Hour":
            return func.date_format(column, "00:%M")
        if format == "Hour of Day":
            return func.date_format(column, "%H:00")
        if format == "Day of Week":
            return func.date_format(column, "%W")
        if format == "Day of Month":
            return func.date_format(column, "%d")
        if format == "Day of Year":
            return func.date_format(column, "%j")
        if format == "Month of Year":
            return func.date_format(column, "%M")
        if format == "Quarter of Year":
            return func.quarter(column)
        if format == "Quarter":
            # 2022-02-12 -> 2022-01-01
            # STR_TO_DATE(CONCAT(YEAR(CURRENT_DATE), '-', (QUARTER(CURRENT_DATE) * 3) - 2, '-01'), '%Y-%m-%d')
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
    lft_rgt = select(Tree.c.lft, Tree.c.rgt).where(Tree.c.name == node).alias("lft_rgt")
    return (
        (select(Tree.c.name).where(Tree.c.lft > lft_rgt.c.lft).where(Tree.c.rgt < lft_rgt.c.rgt))
        if not include_self
        else (
            select(Tree.c.name)
            .where(Tree.c.lft >= lft_rgt.c.lft)
            .where(Tree.c.rgt <= lft_rgt.c.rgt)
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
            return func.sum(case((args[0], 1), else_=0))

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
            return func.sum(case((args[0], args[1]), else_=0))

        # three arg functions

        if function == "between":
            dates = add_start_and_end_time([args[1], args[2]])
            return args[0].between(*dates)

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
            # return case(conditions, else_=default)
            return case(*conditions, else_=default)

        if function == "timespan":
            column = args[0]
            timespan = args[1].lower()  # "last 7 days"
            timespan = timespan[:-1] if timespan.endswith("s") else timespan  # "last 7 day"

            units = [
                "day",
                "week",
                "month",
                "quarter",
                "year",
                "fiscal year",
            ]
            if not any(timespan.endswith(unit) for unit in units):
                raise Exception(f"Invalid timespan unit - {timespan}")

            dates = get_date_range(timespan)
            if not dates:
                raise Exception(f"Invalid timespan {args[1]}")
            dates_str = add_start_and_end_time(dates)
            return column.between(*dates_str)

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
                raise Exception(f"Invalid unit {unit}. Valid units are {', '.join(VALID_UNITS)}")
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

        if function == "date_format":
            return ColumnFormatter.format_date(args[1], args[0])

        if function == "start_of":
            valid_units = ["day", "week", "month", "quarter", "year"]
            unit = args[0].lower()
            if unit not in valid_units:
                raise Exception(f"Invalid unit {unit}. Valid units are {', '.join(valid_units)}")
            return ColumnFormatter.format_date(args[0].title(), args[1])

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
    if unit == "fiscal year":
        return [get_fy_start(today), get_fiscal_year_ending(today)]


def get_fiscal_year_start_date():
    fiscal_year_start = frappe.db.get_single_value("Insights Settings", "fiscal_year_start")
    if not fiscal_year_start or get_date_str(fiscal_year_start) == "0001-01-01":
        return getdate("1995-04-01")
    return getdate(fiscal_year_start)


def get_fy_start(date):
    fy_start = get_fiscal_year_start_date()
    dt = getdate(date)  # eg. 2019-01-01
    if dt.month < fy_start.month:
        return getdate(f"{dt.year - 1}-{fy_start.month}-{fy_start.day}")  # eg. 2018-04-01
    return getdate(f"{dt.year}-{fy_start.month}-{fy_start.day}")  # eg. 2019-04-01


def get_fiscal_year_ending(date):
    fy_start = get_fiscal_year_start_date()
    fy_end = add_to_date(fy_start, years=1, days=-1)
    dt = getdate(date)  # eg. 2019-04-01
    if dt.month < fy_start.month:
        return getdate(f"{dt.year}-{fy_end.month}-{fy_end.day}")  # eg. 2018-03-31
    return getdate(f"{dt.year + 1}-{fy_end.month}-{fy_end.day}")  # eg. 2019-03-31


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
            get_first_day_of_week(add_to_date(today, days=direction * 7 * number_of_unit)),
            get_last_day_of_week(add_to_date(today, days=direction * 7)),
        ]
    if unit == "month":
        dates = [
            get_first_day(add_to_date(today, months=direction * number_of_unit)),
            get_last_day(add_to_date(today, months=direction)),
        ]
    if unit == "quarter":
        dates = [
            get_quarter_start(add_to_date(today, months=direction * 3 * number_of_unit)),
            get_quarter_ending(add_to_date(today, months=direction * 3)),
        ]
    if unit == "year":
        dates = [
            get_year_start(add_to_date(today, years=direction * number_of_unit)),
            get_year_ending(add_to_date(today, years=direction)),
        ]
    if unit == "fiscal year":
        dates = [
            get_fy_start(add_to_date(today, years=direction * number_of_unit)),
            get_fiscal_year_ending(add_to_date(today, years=direction)),
        ]

    if dates[0] > dates[1]:
        dates.reverse()
    return dates


def get_date_range(timespan, include_current=False):
    # timespan = "last 7 days" or "next 3 months"
    time_direction = timespan.lower().split(" ")[0]  # "last" or "next" or "current"
    # "day", "week", "month", "quarter", "year", "fiscal year"
    if "fiscal year" in timespan.lower():
        unit = "fiscal year"
    else:
        unit = timespan.lower().split(" ")[-1]

    if time_direction == "current":
        return get_current_date_range(unit)

    number_of_unit = int(timespan.split(" ")[1])  # 7, 3, etc

    if time_direction == "last" or time_direction == "next":
        time_direction = -1 if time_direction == "last" else 1

        dates = get_directional_date_range(time_direction, unit, number_of_unit)

        if include_current:
            current_dates = get_current_date_range(unit)
            dates[0] = min(dates[0], current_dates[0])
            dates[1] = max(dates[1], current_dates[1])

        return dates


def add_start_and_end_time(dates):
    if not dates:
        return dates
    if type(dates[0]) == str:
        return [dates[0] + " 00:00:00", dates[1] + " 23:59:59"]
    if type(dates[0]) == datetime or type(dates[0]) == date:
        return [dates[0].strftime("%Y-%m-%d 00:00:00"), dates[1].strftime("%Y-%m-%d 23:59:59")]


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

    @classmethod
    def is_binary_operator(cls, operator):
        return (
            operator in cls.ARITHMETIC_OPERATIONS
            or operator in cls.COMPARE_OPERATIONS
            or operator in cls.LOGICAL_OPERATIONS
        )


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

        if query.is_native_query:
            return query.sql.strip().rstrip(";") if query.sql else ""
        elif query.is_assisted_query:
            return self.build_assisted_query()
        else:
            self.process_tables_and_joins()
            self.process_columns()
            self.process_filters()
            compiled = self.make_query()
            return str(compiled) if compiled else ""

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
            join_type = _join.get("type", {}).get("value")

            left_table = self.make_table(row.table)
            right_table = self.make_table(_join.get("with", {}).get("value"))

            condition = _join.get("condition")
            left_key = condition.get("left", {}).get("value")
            right_key = condition.get("right", {}).get("value")

            if not left_key or not right_key:
                continue

            left_key = self.make_column(left_key, row.table)
            right_key = self.make_column(right_key, _join.get("with", {}).get("value"))

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
            # hack: to avoid duplicate columns error if tables have same column names
            sql = select(text("t0.*"))
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
            isouter, full = False, False
            if join.type == "left":
                isouter = True
            elif join.type == "full":
                isouter = True
                full = True

            sql = sql.join_from(
                join.left,
                join.right,
                join.left_key == join.right_key,
                isouter=isouter,
                full=full,
            )

        return sql

    def compile(self, query):
        compile_args = {"compile_kwargs": {"literal_binds": True}}
        if self.dialect:
            compile_args["dialect"] = self.dialect
        compiled = query.compile(**compile_args)
        return compiled

    def build_assisted_query(self):
        self._joins = []
        self._filters = None
        self._columns = []
        self._measures = []
        self._dimensions = []
        self._order_by_columns = []
        self._limit = None

        assisted_query = self.query.variant_controller.query_json
        if not assisted_query or not assisted_query.is_valid():
            return ""
        main_table = assisted_query.table.table
        main_table = self.make_table(main_table)

        for join in assisted_query.joins:
            if not join.is_valid():
                continue
            self._joins.append(
                {
                    "left": self.make_table(join.left_table.table),
                    "right": self.make_table(join.right_table.table),
                    "type": join.join_type.value,
                    "left_key": self.make_column(join.left_column.column, join.left_table.table),
                    "right_key": self.make_column(
                        join.right_column.column, join.right_table.table
                    ),
                }
            )

        def make_sql_column(column, for_filter=False):
            _column = self.make_column(column.column, column.table)
            if column.is_expression():
                _column = self.expression_processor.process(column.expression.ast)

            if column.is_aggregate() and column.aggregation.lower() != "group by":
                _column = self.aggregations.apply(column.aggregation, _column)

            if column.has_granularity() and not for_filter:
                _column = self.column_formatter.format_date(column.granularity, _column)
            return _column.label(column.alias)

        if assisted_query.filters:
            filters = []
            for fltr in assisted_query.filters:
                if not fltr.is_valid():
                    continue
                if fltr.expression:
                    _filter = self.expression_processor.process(fltr.expression.ast)
                    filters.append(_filter)
                    continue
                _column = make_sql_column(fltr.column, for_filter=True)
                filter_value = fltr.value.value or ""
                operator = fltr.operator.value

                if BinaryOperations.is_binary_operator(operator):
                    operation = BinaryOperations.get_operation(operator)
                    _filter = operation(_column, filter_value)
                elif "set" in operator:  # is set, is not set
                    _filter = Functions.apply(operator, _column)
                elif operator == "is":
                    fn = "is_set" if filter_value.lower() == "set" else "is_not_set"
                    _filter = Functions.apply(fn, _column)
                else:
                    args = [filter_value]
                    if operator == "between":
                        args = filter_value.split(",")
                    elif operator == "in" or operator == "not_in":
                        if filter_value and isinstance(filter_value[0], dict):
                            args = [val["value"] for val in filter_value]
                        else:
                            args = filter_value
                    _filter = Functions.apply(operator, _column, *args)

                filters.append(_filter)
            self._filters = and_(*filters)

        for column in assisted_query.columns:
            if not column.is_valid():
                continue
            if column.is_measure():
                self._measures.append(make_sql_column(column))
            if column.is_dimension():
                self._dimensions.append(make_sql_column(column))
            if column.order:
                _column = make_sql_column(column)
                self._order_by_columns.append(
                    _column.asc() if column.order == "asc" else _column.desc()
                )

        self._limit = assisted_query.limit or None

        columns = self._dimensions + self._measures
        if not columns:
            columns = [text("t0.*")]

        # TODO: validate if all column tables are selected

        query = select(*columns).select_from(main_table)
        for join in self._joins:
            query = query.join_from(
                join["left"],
                join["right"],
                join["left_key"] == join["right_key"],
                isouter=join["type"] != "inner",
                full=join["type"] == "full",
            )

        if self._filters is not None:
            query = query.where(self._filters)
        if self._dimensions:
            query = query.group_by(*self._dimensions)
        if self._order_by_columns:
            query = query.order_by(*self._order_by_columns)
        if self._limit:
            query = query.limit(self._limit)
        if not columns:
            # if select * query then limit to 50 rows
            query = query.limit(50)

        return self.compile(query)
