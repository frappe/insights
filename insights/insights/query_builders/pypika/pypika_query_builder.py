# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from pypika import Order
from pypika.enums import JoinType

from ..models import QueryBuilder
from frappe import _dict, parse_json
from .helpers import ColumnProcessor, ExpressionProcessor
from insights.insights.doctype.insights_query.insights_query import InsightsQuery


class PypikaQueryBuilder(QueryBuilder):
    query_cls = None
    column_processor = ColumnProcessor()
    expression_processor = ExpressionProcessor()

    def build(self, query: InsightsQuery):
        self.query = query
        self.process_tables()
        self.process_joins()
        self.process_columns()
        self.process_filters()
        self.process_limit()
        return self.make_query()

    def process_tables(self):
        """converts the insights tables into a sql tables and appends it to self._tables"""
        self._tables = []
        for row in self.query.tables:
            table = self.query_cls.Table(row.table)
            if table not in self._tables:
                self._tables.append(table)

    def process_joins(self):
        """converts the insights joins into a sql joins and appends it to self._joins"""
        self._joins = []
        for table in self.query.tables:
            if not table.join:
                continue

            # TODO: validate table.join
            _join = parse_json(table.join)
            LeftTable = self.query_cls.Table(table.table)
            RightTable = self.query_cls.Table(_join.get("with").get("value"))
            join_type = _join.get("type").get("value")
            condition = _join.get("condition").get("value")
            left_key = condition.split("=")[0].strip()
            right_key = condition.split("=")[1].strip()

            self._joins.append(
                _dict(
                    {
                        "left": LeftTable,
                        "right": RightTable,
                        "type": JoinType[join_type],
                        "condition": LeftTable[left_key] == RightTable[right_key],
                    }
                )
            )

    def process_columns(self):
        """converts the insights columns into a sql columns and appends it to self._columns"""
        self._columns = []
        self._group_by_columns = []
        self._order_by_columns = []

        for row in self.query.columns:
            if not row.is_expression:
                _column = self.column_processor.make_column(row.column, row.table)
                _column = self.column_processor.process_format(
                    parse_json(row.format_option), row.type, _column
                )
                _column = self.column_processor.process_aggregation(
                    row.aggregation, _column
                )
            else:
                expression = parse_json(row.expression)
                _column = self.expression_processor.process(expression.get("ast"))
                _column = self.column_processor.process_format(row, _column)

            self.process_sorting(row, _column)
            _column = _column.as_(row.label) if row.label else _column
            if row.aggregation == "Group By":
                self._group_by_columns.append(_column)

            self._columns.append(_column)

    def process_sorting(self, row, column):
        if row.order_by:
            self._order_by_columns.append((column, row.order_by))
        return column

    def process_filters(self):
        """converts the insights filters into a pypika filters and appends it to self._filters"""
        filters = parse_json(self.query.filters)
        self._filters = self.expression_processor.process(filters)

    def process_limit(self):
        self._limit: int = self.query.limit or 10

    def make_query(self):
        query = self.query_cls

        for table in self._tables:
            query = query.from_(table)
            if self._joins:
                joins = [d for d in self._joins if d.left == table]
                for join in joins:
                    query = query.join(join.right, join.type).on(join.condition)

        if not self._columns and self._tables:
            query = query.select("*")

        for column in self._columns:
            query = query.select(column)

        if self._group_by_columns:
            query = query.groupby(*self._group_by_columns)

        if self._order_by_columns:
            for column, order in self._order_by_columns:
                query = query.orderby(column, order=Order[order])

        query = query.where(self._filters)

        query = query.limit(self._limit)

        return query.get_sql()
