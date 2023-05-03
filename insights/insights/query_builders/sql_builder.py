import operator
from contextlib import suppress

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
from sqlalchemy import Column, Integer
from sqlalchemy import column as sa_column
from sqlalchemy import literal_column, select, table
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import column_property
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
            return func.date_format(column, "%Y-%m-%d %H:%i")
        if format == "Hour":
            return func.date_format(column, "%Y-%m-%d %H:00")
        if format == "Day" or format == "Day Short":
            return func.date_format(column, "%Y-%m-%d")
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
        )
        if not include_self
        else (
            select([Tree.c.name])
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
            timespan = args[1].lower()  # "last 7 days"
            timespan = (
                timespan[:-1] if timespan.endswith("s") else timespan
            )  # "last 7 day"

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
    if unit == "fiscal year":
        return [get_fy_start(today), get_fiscal_year_ending(today)]


def get_fiscal_year_start_date():
    return getdate(
        frappe.db.get_single_value("Insights Settings", "fiscal_year_start")
        or "1995-04-01"
    )


def get_fy_start(date):
    fy_start = get_fiscal_year_start_date()
    dt = getdate(date)  # eg. 2019-01-01
    if dt.month < fy_start.month:
        return getdate(
            f"{dt.year - 1}-{fy_start.month}-{fy_start.day}"
        )  # eg. 2018-04-01
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
            return self.builder.get_or_set_column(column, table)

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
        self._query = None
        self._tables = {}
        self._limit = 500

    def build(self, query, dialect: Dialect = None):
        self.query = query
        self.dialect = dialect

        if query.is_native_query:
            return query.sql.strip().rstrip(";") if query.sql else ""

        if not query.tables:
            return ""

        self.process_table_schema()
        self.process_tables_and_joins()
        self.process_columns()
        self.process_filters()
        self._query = self._query.limit(self.query.limit or self._limit)
        self._query = self.compile(self._query)
        return str(self._query) if self._query else ""

    def get_or_set_table(self, name):
        if not hasattr(self, "_tables"):
            self._tables = {}

        if name in self._tables:
            return self._tables[name]

        _table = table(name)
        self._tables[name] = _table
        return self._tables[name]

    def get_or_set_column(self, columnname, tablename):
        if columnname == "count":
            return func.count(literal_column("*")).label("count")

        _table = self.get_or_set_table(tablename)
        if hasattr(_table.c, columnname):
            return _table.c[columnname]

        _column = Column(columnname)
        if custom_column := self.get_custom_column(columnname, tablename):
            _column = custom_column[0]
            _table._columns.add(_column)
        else:
            _table.append_column(_column)
        return _table.c[columnname]

    def get_custom_column(self, columnname, tablename):
        _tablename = frappe.db.get_value(
            "Insights Table", {"table": tablename}, "name"
        )  # add data source filter

        custom_column = frappe.db.get_value(
            "Insights Table Column",
            {
                "column": columnname,
                "parent": _tablename,
                "is_custom": 1,
            },
            ["custom_definition", "column"],
            as_dict=True,
        )
        if not custom_column:
            return None

        sql = parse_json(custom_column.custom_definition).get("sql")
        if not sql:
            return None
        return [literal_column(sql).label(custom_column.column)]

    def process_table_schema(self):
        """
        Finds all tables and columns in the query
        and creates SQLAlchemy models for them under self._tables
        """
        self.Base = declarative_base()
        for row in self.query.tables:
            self.get_or_set_table(row.table)
            if not row.join:
                continue
            _join = parse_json(row.join)
            right_table = _join.get("with").get("value")
            condition = _join.get("condition")
            left_column = condition.get("left").get("value")
            right_column = condition.get("right").get("value")
            self.get_or_set_table(right_table)
            self.get_or_set_column(left_column, row.table)
            self.get_or_set_column(right_column, _join.get("with").get("value"))

        for column in self.query.columns:
            if not column.is_expression:
                self.get_or_set_column(column.column, column.table)
            else:
                expression = parse_json(column.expression)
                # processing expression to get columns
                self.expression_processor.process(expression.get("ast"))

        # processing filters to get columns
        self.expression_processor.process(parse_json(self.query.filters))

    def process_tables_and_joins(self):
        main_table = self.query.tables[0].table
        self._query = select(self._tables[main_table])

        for row in self.query.tables:
            if not row.join:
                continue

            _join = parse_json(row.join)
            join_type = _join.get("type").get("value")
            left_table = self.get_or_set_table(row.table)
            right_table = self.get_or_set_table(_join.get("with").get("value"))

            condition = _join.get("condition")
            left_key = condition.get("left").get("value")
            right_key = condition.get("right").get("value")

            left_key = self.get_or_set_column(left_key, row.table)
            right_key = self.get_or_set_column(
                right_key, _join.get("with").get("value")
            )

            self._query = self._query.join_from(
                left_table,
                right_table,
                left_key == right_key,
                full=join_type == "full",
                isouter=join_type != "inner",
            )

    def process_columns(self):
        self._query = self._query.with_only_columns([])
        if not self.query.columns:
            self._query = select([literal_column("*")]).select_from(self._query)
            return
        for column in self.query.columns:
            if not column.is_expression:
                _column = self.get_or_set_column(column.column, column.table)
                _column = self.column_formatter.format(
                    parse_json(column.format_option), column.type, _column
                )
                _column = self.aggregations.apply(column.aggregation, _column)
            else:
                expression = parse_json(column.expression)
                _column = self.expression_processor.process(expression.get("ast"))
                _column = self.column_formatter.format(
                    parse_json(column.format_option), column.type, _column
                )

            labelled_column = _column.label(column.label) if column.label else _column
            self._query = self._query.add_columns(labelled_column)

            if column.order_by:
                self._query = self._query.order_by(
                    labelled_column.asc()
                    if column.order_by == "asc"
                    else labelled_column.desc()
                )

            if column.aggregation == "Group By":
                self._query = self._query.group_by(labelled_column)

    def process_filters(self):
        filters = parse_json(self.query.filters)
        filters = self.expression_processor.process(filters)
        self._query = self._query.filter(filters) if filters else self._query

    def compile(self, query):
        compile_args = {"compile_kwargs": {"literal_binds": True}}
        if self.dialect:
            compile_args["dialect"] = self.dialect
        compiled = query.compile(**compile_args)
        return compiled
