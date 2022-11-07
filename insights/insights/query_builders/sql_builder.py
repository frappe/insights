# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from json import loads

from pypika import Order
from pypika.enums import JoinType

import frappe
from frappe import _dict
from frappe.query_builder import Table


from insights.insights.doctype.insights_query.utils import (
    parse_query_expression,
    build_query_field,
    Aggregations,
    ColumnFormat,
)

from .models import QueryBuilder
from insights.insights.doctype.insights_query.insights_query import InsightsQuery


class SQLQueryBuilder(QueryBuilder):
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
            table = Table(row.table)
            if table not in self._tables:
                self._tables.append(table)

    def process_joins(self):
        """converts the insights joins into a sql joins and appends it to self._joins"""
        self._joins = []
        for table in self.query.tables:
            if not table.join:
                continue

            # TODO: validate table.join
            _join = frappe.parse_json(table.join)
            LeftTable = Table(table.table)
            RightTable = Table(_join.get("with").get("value"))
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
                _column = self.process_dimension_or_metric(row)
            else:
                expression = frappe.parse_json(row.expression)
                _column = parse_query_expression(expression.get("ast"))
                _column = self.process_column_format(row, _column)

            self.process_sorting(row, _column)
            _column = _column.as_(row.label) if row.label else _column
            if row.aggregation == "Group By":
                self._group_by_columns.append(_column)

            self._columns.append(_column)

    def process_dimension_or_metric(self, row):
        _column = build_query_field(row.table, row.column)
        # dates should be formatted before aggregagtions
        _column = self.process_column_format(row, _column)
        _column = self.process_aggregation(row, _column)
        return _column

    def process_column_format(self, row, column):
        if row.format_option and row.type in ("Date", "Datetime"):
            format_option = frappe.parse_json(row.format_option)
            return ColumnFormat.format_date(format_option.date_format, column)
        return column

    def process_aggregation(self, row, column):
        if not row.aggregation or row.aggregation == "Group By":
            return column

        elif not Aggregations.is_valid(row.aggregation.lower()):
            frappe.throw("Invalid aggregation function: {}".format(row.aggregation))

        else:
            return Aggregations.apply(row.aggregation.lower(), column)

    def process_sorting(self, row, column):
        if not row.order_by:
            return column

        if row.type in ("Date", "Datetime") and row.format_option:
            format_option = frappe.parse_json(row.format_option)
            date = ColumnFormat.parse_date(format_option.date_format, column)
            self._order_by_columns.append((date, row.order_by))
        else:
            self._order_by_columns.append((column, row.order_by))

    def process_filters(self):
        """converts the insights filters into a pypika filters and appends it to self._filters"""
        filters = frappe.parse_json(self.query.filters)
        self._filters = parse_query_expression(filters)

    def process_limit(self):
        self._limit: int = self.query.limit or 10

    def make_query(self):
        """uses self._tables, self._joins, self._columns, self._filters, self._limit to build the query and stores it in self._query"""
        query = frappe.qb

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
