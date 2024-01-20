from contextlib import suppress

from frappe import _dict, parse_json
from sqlalchemy import column as sa_column
from sqlalchemy import select, table
from sqlalchemy.sql import and_, or_, text

from .sql_functions import Aggregations, BinaryOperations, ColumnFormatter, Functions


class LegacyQueryBuilder:
    def __init__(self, engine) -> None:
        self.functions = Functions
        self.aggregations = Aggregations
        self.column_formatter = ColumnFormatter
        self.expression_processor = ExpressionProcessor(self)
        self.engine = engine

    def build(self, query):
        self.query = query
        self.process_tables_and_joins()
        self.process_columns()
        self.process_filters()
        compiled = self.make_query()
        return str(compiled) if compiled else ""

    def make_table(self, name):
        if not hasattr(self, "_tables"):
            self._tables = {}
        if name not in self._tables:
            self._tables[name] = table(name).alias(f"{name}")
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

        main_table = self.query.tables[0].table

        sql = None
        if not self._columns:
            # hack: to avoid duplicate columns error if tables have same column names
            sql = select(text(f"`{main_table}`.*"))
        else:
            sql = select(*self._columns)

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

        return sql.compile(self.engine, compile_kwargs={"literal_binds": True})

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


class ExpressionProcessor:
    def __init__(self, builder: "LegacyQueryBuilder"):
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
