# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re
import time
from copy import deepcopy
from json import dumps, loads

import frappe
from frappe import _dict
from frappe.model.document import Document
from frappe.query_builder import Criterion, Field, Table
from frappe.utils import cint, cstr, flt
from pypika import Order
from sqlparse import format as format_sql

from analytics.analytics.doctype.query.utils import (
    Aggregations,
    ColumnFormat,
    Operations,
)


class Query(Document):
    def validate(self):
        # TODO: validate if a column is an expression and aggregation is "group by"
        pass

    def on_trash(self):
        charts = frappe.get_all(
            "Query Chart", filters={"query": self.name}, pluck="name"
        )
        for chart in charts:
            frappe.delete_doc("Query Chart", chart)

    @frappe.whitelist()
    def add_table(self, table):
        new_table = {
            "label": table.get("label"),
            "table": table.get("table"),
        }
        self.append("tables", new_table)
        self.save()

    @frappe.whitelist()
    def remove_table(self, table):
        for row in self.tables:
            if row.get("name") == table.get("name"):
                self.remove(row)
                break

        self.save()

    @frappe.whitelist()
    def add_column(self, column):
        new_column = {
            "type": column.get("type"),
            "label": column.get("label"),
            "table": column.get("table"),
            "column": column.get("column"),
            "table_label": column.get("table_label"),
            "aggregation": column.get("aggregation"),
        }
        self.append("columns", new_column)
        self.save()

    @frappe.whitelist()
    def move_column(self, from_index, to_index):
        self.columns.insert(to_index, self.columns.pop(from_index))
        for row in self.columns:
            row.idx = self.columns.index(row) + 1
        self.save()

    @frappe.whitelist()
    def update_column(self, column):
        for row in self.columns:
            if row.get("name") == column.get("name"):
                row.label = column.get("label")
                row.format = column.get("format")
                row.order_by = column.get("order_by")
                row.aggregation = column.get("aggregation")
                row.aggregation_condition = column.get("aggregation_condition")
                break

        self.save()

    @frappe.whitelist()
    def remove_column(self, column):
        for row in self.columns:
            if row.get("name") == column.get("name"):
                self.remove(row)
                break

        self.save()

    @frappe.whitelist()
    def update_filters(self, filters):
        sanitized_conditions = self.sanitize_conditions(filters.get("conditions"))
        filters["conditions"] = sanitized_conditions or []
        self.filters = dumps(filters, indent=2, default=cstr)
        self.save()

    def sanitize_conditions(self, conditions):
        if not conditions:
            return

        _conditions = deepcopy(conditions)

        for idx, condition in enumerate(_conditions):
            if "conditions" not in condition:
                # TODO: validate if condition is valid
                continue

            sanitized_conditions = self.sanitize_conditions(condition.get("conditions"))
            if sanitized_conditions:
                conditions[idx]["conditions"] = sanitized_conditions
            else:
                # remove the condition if it has zero conditions
                conditions.remove(condition)

        return conditions

    @frappe.whitelist()
    def apply_transform(self, type, data):
        self.transform_type = type
        self.transform_data = dumps(data, indent=2, default=cstr)
        if type == "Pivot":
            self.pivot(data)

        self.save()

    def pivot(self, transform_data):
        from pandas import DataFrame

        # TODO: validate if two columns doesn't have same label

        result = loads(self.result)
        columns = [d.get("label") for d in self.get("columns")]

        dataframe = DataFrame(columns=columns, data=result)
        pivoted = dataframe.pivot(
            index=transform_data.get("index_columns"),
            columns=transform_data.get("pivot_columns"),
        )

        self.transform_result = pivoted.to_html()
        self.transform_result = self.transform_result.replace("NaN", "-")

    @frappe.whitelist()
    def get_selectable_tables(self):
        if not self.tables:
            return frappe.get_all(
                "Table",
                filters={"data_source": self.data_source},
                fields=["table", "label"],
            )
        else:
            tables = [d.table for d in self.tables]
            Table = frappe.qb.DocType("Table")
            TableLink = frappe.qb.DocType("Table Link")
            query = (
                frappe.qb.from_(Table)
                .from_(TableLink)
                .select(
                    TableLink.foreign_table.as_("table"),
                    TableLink.foreign_table_label.as_("label"),
                )
                .where((TableLink.parent == Table.name) & (Table.table.isin(tables)))
            )
            return query.run(as_dict=True)

    @frappe.whitelist()
    def get_selectable_columns(self):
        if not self.tables:
            return []

        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        columns = []
        for table in self.tables:
            columns += data_source.get_columns(table)
        return columns

    @frappe.whitelist()
    def set_limit(self, limit):
        sanitized_limit = cint(limit)
        if not sanitized_limit or sanitized_limit < 0:
            frappe.throw("Limit must be a positive integer")
        self.limit = sanitized_limit
        self.save()

    @frappe.whitelist()
    def get_column_values(self, column, search_text):
        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        return data_source.get_distinct_column_values(column, search_text)

    @frappe.whitelist()
    def run(self):
        if not self.columns or not self.filters:
            return

        self.process()
        self.build()
        self.update_query()
        self.execute()
        self.update_result()
        self.save()

    def process(self):
        self._tables = []
        self.process_columns()
        self.process_filters()
        self.process_limit()

    def build(self):
        query = frappe.qb

        for table in self._tables:
            query = query.from_(table)

        for column in self._columns:
            query = query.select(column)

        if self._group_by_columns:
            query = query.groupby(*self._group_by_columns)

        if self._order_by_columns:
            for column, order in self._order_by_columns:
                query = query.orderby(column, order=Order[order])

        query = query.where(*self._filters)

        query = query.limit(self._limit)

        self._query = query

    def execute(self):
        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        start = time.time()
        result = data_source.execute(self.sql, debug=True)
        end = time.time()
        self._result = list(result)
        self.execution_time = flt(end - start, 3)
        self.last_execution = frappe.utils.now()

    def update_query(self):
        self.sql = format_sql(
            str(self._query), keyword_case="upper", reindent_aligned=True
        )

    def update_result(self):
        self.result = dumps(self._result, default=cstr)

    def process_columns(self):
        self._columns = []
        self._group_by_columns = []
        self._order_by_columns = []

        for row in self.columns:
            _column = self.process_query_field(row.table, row.column)

            if row.format:
                _column = self.process_column_format(row, _column)

            if row.aggregation:
                _column = self.process_aggregation(row, _column)

            if row.order_by:
                self.process_sorting(row, _column)

            _column = _column.as_(row.label)

            self._columns.append(_column)

    def process_column_format(self, row, column):
        if row.type in ("Date", "Datetime"):
            return ColumnFormat.format_date(row.format, column)

    def process_aggregation(self, row, column):
        if row.aggregation == "Count Distinct":
            column = Aggregations.apply("Distinct", column)
            column = Aggregations.apply("Count", column)

        elif row.aggregation == "Count if" and row.aggregation_condition:
            conditions = [
                self.process_simple_filter(condition)
                for condition in loads(row.aggregation_condition)
            ]
            column = Aggregations.apply(
                "Count if", conditions=Criterion.all(conditions)
            )

        elif row.aggregation != "Group By":
            column = Aggregations.apply(row.aggregation, column)

        elif row.aggregation == "Group By":
            self._group_by_columns.append(column)

        return column

    def process_sorting(self, row, column):
        if row.type in ("Date", "Datetime") and row.format:
            date = ColumnFormat.parse_date(row.format, column)
            self._order_by_columns.append((date, row.order_by))
        else:
            self._order_by_columns.append((column, row.order_by))

    def process_filters(self):
        filters = _dict(loads(self.filters))

        def process_filter_group(filter_group):
            _filters = []
            for _filter in filter_group.get("conditions"):
                _filter = _dict(_filter)
                if _filter.group_operator:
                    group_condition = process_filter_group(_filter)
                    GroupCriteria = (
                        Criterion.all
                        if _filter.group_operator == "&"
                        else Criterion.any
                    )
                    _filters.append(GroupCriteria(group_condition))
                else:
                    expression = self.process_expression(_filter)
                    _filters.append(expression)

            return _filters

        RootCriteria = Criterion.all if filters.group_operator == "&" else Criterion.any
        _filters = process_filter_group(filters)
        self._filters = [RootCriteria(_filters)]

    def process_expression(self, condition):
        condition = _dict(condition)
        condition.left = _dict(condition.left)
        condition.right = _dict(condition.right)
        condition.operator = _dict(condition.operator)

        def is_literal_value(term):
            return "value" in term

        def is_query_field(term):
            return "table" in term and "column" in term

        def is_expression(term):
            return "left" in term and "right" in term and "operator" in term

        def process_term(term):
            if is_expression(term):
                return self.process_expression(term)

            if is_query_field(term):
                return self.process_query_field(term.table, term.column)

            if is_literal_value(term):
                return self.process_literal_value(term, condition.operator)

        operation = Operations.get_operation(condition.operator.value)
        condition_left = process_term(condition.left)
        condition_right = process_term(condition.right)

        return operation(condition_left, condition_right)

    def process_literal_value(self, literal, operator):
        if "like" in operator.value:
            return f"%{literal.value}%"

        if "in" in operator.value or "between" in operator.value:
            return [d.lstrip().rstrip() for d in literal.value.split(",")]

        if "set" in operator.value:
            return None

        return literal.value

    def process_limit(self):
        self._limit: int = self.limit or 10

    def process_query_field(self, table, column) -> Field:
        table = Table(table)
        Field = table[column]

        # only add table to query if a column or filter from the table present
        if table not in self._tables:
            self._tables.append(table)

        return Field
