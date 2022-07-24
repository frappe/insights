# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from json import dumps, loads

import frappe
from frappe import _dict
from frappe.query_builder import Table
from frappe.utils import cstr, flt
from sqlparse import format as format_sql

from pypika import Order
from pypika.enums import JoinType

from insights.insights.doctype.query.utils import (
    parse_query_expression,
    make_query_field,
    Aggregations,
    ColumnFormat,
)

from insights.insights.doctype.query.query_client import QueryClient


class Query(QueryClient):
    def validate(self):
        # TODO: validate if a column is an expression and aggregation is "group by"
        self.validate_limit()
        self.validate_filters()

    def validate_limit(self):
        if self.limit and self.limit < 1:
            frappe.throw("Limit must be greater than 0")
        if self.limit and self.limit > 1000:
            frappe.throw("Limit must be less than 1000")

    def validate_filters(self):
        if not self.filters:
            self.filters = dumps(
                {
                    "type": "LogicalExpression",
                    "operator": "&&",
                    "level": 1,
                    "position": 1,
                    "conditions": [],
                },
                indent=2,
            )

    def on_update(self):
        # create a query visualization if not exists
        visualizations = self.get_visualizations()
        if not visualizations:
            frappe.get_doc(
                {
                    "doctype": "Query Visualization",
                    "query": self.name,
                    "title": self.title,
                }
            ).insert()

    def on_trash(self):
        visualizations = self.get_visualizations()
        for visualization in visualizations:
            frappe.delete_doc("Query Visualization", visualization)

    def before_save(self):
        if self.get("skip_before_save"):
            self.skip_before_save = False
            return

        if not self.columns or not self.filters:
            return

        self.process()
        self.build()
        self.update_query()

    def process(self):
        self.process_tables()
        self.process_joins()
        self.process_columns()
        self.process_filters()
        self.process_limit()

    def build(self):
        query = frappe.qb

        for table in self._tables:
            query = query.from_(table)
            if self._joins:
                joins = [d for d in self._joins if d.left == table]
                for join in joins:
                    query = query.join(join.right, join.type).on(join.condition)

        for column in self._columns:
            query = query.select(column)

        if self._group_by_columns:
            query = query.groupby(*self._group_by_columns)

        if self._order_by_columns:
            for column, order in self._order_by_columns:
                query = query.orderby(column, order=Order[order])

        query = query.where(self._filters)

        query = query.limit(self._limit)

        self._query = query

    def update_query(self):
        updated_query = format_sql(
            str(self._query), keyword_case="upper", reindent_aligned=True
        )
        if self.sql == updated_query:
            return

        self.sql = updated_query
        self.status = "Pending Execution"

    def execute(self):
        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        start = time.time()
        result = data_source.execute_query(self.sql, debug=True)
        end = time.time()
        self._result = list(result)
        self.execution_time = flt(end - start, 3)
        self.last_execution = frappe.utils.now()

    def update_result(self):
        self.result = dumps(self._result, default=cstr)
        self.status = "Execution Successful"

    def process_tables(self):
        self._tables = []
        for row in self.tables:
            table = Table(row.table)
            if table not in self._tables:
                self._tables.append(table)

    def process_joins(self):
        self._joins = []
        for table in self.tables:
            if not table.join:
                continue

            # TODO: validate table.join
            _join = loads(table.join)
            LeftTable = Table(table.table)
            RightTable = Table(_join.get("with").get("value"))
            join_type = _join.get("type").get("value")
            key = _join.get("key").get("value")

            self._joins.append(
                _dict(
                    {
                        "left": LeftTable,
                        "right": RightTable,
                        "type": JoinType[join_type],
                        "condition": LeftTable["name"] == RightTable[key],
                    }
                )
            )

    def process_columns(self):
        self._columns = []
        self._group_by_columns = []
        self._order_by_columns = []

        for row in self.columns:
            if not row.is_expression:
                _column = self.process_dimension_or_metric(row)
            else:
                expression = loads(row.expression)
                _column = parse_query_expression(expression.get("ast"))

            self.process_sorting(row, _column)
            _column = _column.as_(row.label)
            self._columns.append(_column)

    def process_dimension_or_metric(self, row):
        _column = make_query_field(row.table, row.column)
        # dates should be formatted before aggregagtions
        _column = self.process_column_format(row, _column)
        _column = self.process_aggregation(row, _column)
        return _column

    def process_column_format(self, row, column):
        if row.format_option and row.type in ("Date", "Datetime"):
            format_option = _dict(loads(row.format_option))
            return ColumnFormat.format_date(format_option.date_format, column)
        return column

    def process_aggregation(self, row, column):
        if not row.aggregation:
            return column

        if row.aggregation == "Group By":
            self._group_by_columns.append(column)

        elif not Aggregations.is_valid(row.aggregation.lower()):
            frappe.throw("Invalid aggregation function: {}".format(row.aggregation))

        else:
            column = Aggregations.apply(row.aggregation.lower(), column)

        return column

    def process_sorting(self, row, column):
        if not row.order_by:
            return column

        if row.type in ("Date", "Datetime") and row.format_option:
            format_option = _dict(loads(row.format_option))
            date = ColumnFormat.parse_date(format_option.date_format, column)
            self._order_by_columns.append((date, row.order_by))
        else:
            self._order_by_columns.append((column, row.order_by))

    def process_filters(self):
        filters = _dict(loads(self.filters))
        self._filters = parse_query_expression(filters)

    def process_limit(self):
        self._limit: int = self.limit or 10
