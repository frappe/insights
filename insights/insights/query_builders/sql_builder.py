from typing import List

import frappe
from frappe import _dict
from sqlalchemy import Column, TextClause
from sqlalchemy import column as sa_column
from sqlalchemy import select, table
from sqlalchemy.sql import and_, func, text

from insights.insights.doctype.insights_query.utils import Column as AssistedQueryColumn
from insights.insights.doctype.insights_query.utils import Filter as AssistedQueryFilter
from insights.insights.doctype.insights_query.utils import Join as AssistedQueryJoin
from insights.insights.doctype.insights_query.utils import Query as AssistedQuery

from .legacy_query_builder import LegacyQueryBuilder
from .sql_functions import (
    Aggregations,
    BinaryOperations,
    ColumnFormatter,
    Functions,
    call_function,
    get_eval_globals,
)
from .utils import process_raw_expression


class SQLQueryBuilder:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.functions = Functions
        self.aggregations = Aggregations
        self.column_formatter = ColumnFormatter

    def build(self, query):
        if query.is_native_query:
            return query.sql.strip().rstrip(";") if query.sql else ""
        elif query.is_assisted_query:
            return self.process_and_build(query)
        return LegacyQueryBuilder(self.engine).build(query)

    def process_and_build(self, query) -> str:
        assisted_query: AssistedQuery = query.variant_controller.query_json
        if not assisted_query or not assisted_query.is_valid():
            return ""

        query = ""
        frappe.flags._current_query_dialect = self.engine.dialect
        try:
            self._process(assisted_query)
            query = self._build(assisted_query)
            query = self.compile_query(query)
        finally:
            frappe.flags._current_query_dialect = None
        return query

    def _process(self, assisted_query: AssistedQuery):
        self._tables = {}
        self._joins = []
        self._filters = None
        self._columns = []
        self._measures = []
        self._dimensions = []
        self._order_by_columns = []
        self._limit = None

        self.process_joins(assisted_query.joins)
        self.process_filters(assisted_query.filters)
        self.process_columns(assisted_query.columns)

        self._limit = assisted_query.limit or None

    def process_joins(self, joins: List[AssistedQueryJoin]):
        if not joins:
            return
        for join in joins:
            if not join.is_valid():
                continue
            self._joins.append(
                _dict(
                    left=self.make_table(join.left_table.table),
                    right=self.make_table(join.right_table.table),
                    type=join.join_type.value,
                    left_key=self.make_column(join.left_column.column, join.left_table.table),
                    right_key=self.make_column(join.right_column.column, join.right_table.table),
                )
            )

    def process_column(self, column: AssistedQueryColumn, for_filter=False):
        _column = self.make_column(column.column, column.table)
        if column.is_expression():
            _column = self.evaluate_expression(column.expression.raw)

        if column.is_aggregate():
            _column = self.aggregations.apply(column.aggregation, _column)

        if column.has_granularity() and not for_filter:
            _column = self.column_formatter.format_date(column.granularity, _column)

        if isinstance(_column, TextClause):
            return _column

        return _column.label(column.alias)

    def process_filters(self, filters: List[AssistedQueryFilter]):
        if not filters:
            return

        _filters = []
        for fltr in filters:
            if not fltr.is_valid():
                continue

            if fltr.expression:
                _filter = self.evaluate_expression(fltr.expression.raw)
                _filters.append(_filter)
                continue

            _column = self.process_column(fltr.column, for_filter=True)
            operator = fltr.operator.value
            filter_value = fltr.value.value or ""

            if BinaryOperations.is_binary_operator(operator):
                operation = BinaryOperations.get_operation(operator)
                _filter = operation(_column, filter_value)
            elif "set" in operator:  # is set, is not set
                _filter = call_function(operator, _column)
            elif operator == "is":
                operator_fn = "is_set" if filter_value.lower() == "set" else "is_not_set"
                _filter = call_function(operator_fn, _column)
            elif operator == "between":
                from_to = filter_value.split(",")
                _filter = call_function(operator, _column, *from_to)
            elif operator == "in" or operator == "not_in":
                args = filter_value
                if filter_value and isinstance(filter_value[0], dict):
                    args = [val["value"] for val in filter_value]
                _filter = call_function(operator, _column, *args)
            else:
                _filter = call_function(operator, _column, filter_value)

            _filters.append(_filter)

        if _filters:
            self._filters = and_(*_filters)

    def process_columns(self, columns: List[AssistedQueryColumn]):
        for column in columns:
            if not column.is_valid():
                continue
            if column.is_measure():
                self._measures.append(self.process_column(column))
            if column.is_dimension():
                self._dimensions.append(self.process_column(column))
            if column.order:
                _column = self.process_column(column)
                self._order_by_columns.append(
                    _column.asc() if column.order == "asc" else _column.desc()
                )

    def quote_identifier(self, identifier):
        return self.engine.dialect.identifier_preparer.quote_identifier(identifier)

    def _build(self, assisted_query):
        main_table = assisted_query.table.table
        main_table = self.make_table(main_table)

        columns = self._dimensions + self._measures
        if not columns:
            columns = [text(f"{self.quote_identifier(main_table.name)}.*")]

        query = select(*columns).select_from(main_table)
        for join in self._joins:
            query = query.join_from(
                join.left,
                join.right,
                join.left_key == join.right_key,
                isouter=join.type != "inner",
                full=join.type == "full",
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

        return query

    def make_table(self, name):
        if name not in self._tables:
            self._tables[name] = table(name).alias(name)
        return self._tables[name]

    def make_column(self, columnname, tablename):
        _table = self.make_table(tablename)
        return sa_column(columnname, _selectable=_table)

    def evaluate_expression(self, raw_expression):
        raw = raw_expression
        try:
            raw = process_raw_expression(raw_expression)
            eval_globals = get_eval_globals()
            eval_globals["column"] = lambda table, column: self.make_column(column, table)
            return frappe.safe_eval(raw, eval_globals=eval_globals)
        except Exception as e:
            raise Exception(f"Invalid expression {raw} - {e}")

    def compile_query(self, query):
        return query.compile(
            dialect=self.engine.dialect,
            compile_kwargs={"literal_binds": True},
        )
