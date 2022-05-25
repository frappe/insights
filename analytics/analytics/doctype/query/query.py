# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from json import dumps, loads

import frappe
from frappe import _dict
from frappe.model.document import Document
from frappe.query_builder import Criterion, Field, Table
from frappe.utils import cint, cstr
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
        self.filters = dumps(filters, indent=2, default=cstr)
        self.save()

    @frappe.whitelist()
    def update_result(self):
        self.execute()
        self.save_result()
        self.db_set("result", self.result)

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
    def get_selectable_columns(self, tables=None, table=None):
        if tables:
            tables = frappe.parse_json(tables)
        if table:
            tables = [table]

        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        columns = []
        for table in tables:
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

    def before_save(self):
        if not self.columns or not self.filters:
            self.result = "[]"
            return

        self.process()
        self.build()
        self.save_query()
        self.execute()
        self.save_result()

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
        self._result = data_source.execute(self.sql, debug=True)
        self._result = list(self._result)

    def save_query(self):
        self.sql = format_sql(
            str(self._query), keyword_case="upper", reindent_aligned=True
        )

    def save_result(self):
        self.result = dumps(self._result, default=cstr)

    def process_columns(self):
        self._columns = []
        self._group_by_columns = []
        self._order_by_columns = []

        for row in self.columns:
            _column = self.convert_to_select_field(row.table, row.column)

            if row.format:
                _column = self.process_column_format(row, _column)

            if row.aggregation:
                _column = self.process_aggregation(row, _column)

            if row.order_by:
                self._order_by_columns.append((_column, row.order_by))

            _column = _column.as_(row.label)

            self._columns.append(_column)

    def process_column_format(self, row, column):
        return ColumnFormat.apply(row.format, column)

    def process_aggregation(self, row, column):
        if row.aggregation != "Group By":
            column = Aggregations.apply(row.aggregation, column)

        if row.aggregation == "Count Distinct":
            column = Aggregations.apply("Distinct", column)
            column = Aggregations.apply("Count", column)

        if row.aggregation == "Group By":
            self._group_by_columns.append(column)

        return column

    def process_filters(self):
        filters = _dict(loads(self.filters))

        def process_filter_group(filter_group):
            _filters = []
            for filter in filter_group.get("conditions"):
                filter = _dict(filter)
                if filter.group_operator:
                    group_condition = process_filter_group(filter)
                    GroupCriteria = (
                        Criterion.all
                        if filter.group_operator == "All"
                        else Criterion.any
                    )
                    _filters.append(GroupCriteria(group_condition))
                else:
                    expression = self.convert_to_expression(filter)
                    _filters.append(expression)

            return _filters

        RootCriteria = (
            Criterion.all if filters.group_operator == "All" else Criterion.any
        )
        _filters = process_filter_group(filters)
        self._filters = [RootCriteria(_filters)]

    def convert_to_expression(self, condition):
        condition = _dict(condition)
        condition.left = _dict(condition.left)
        condition.right = _dict(condition.right)
        condition.operator = _dict(condition.operator)

        operand_1 = self.convert_to_select_field(
            condition.left.table, condition.left.column
        )
        if condition.right_type == "Column":
            operand_2 = self.convert_to_select_field(
                condition.right.table, condition.right.column
            )
        else:
            if "like" in condition.operator.value:
                operand_2 = f"%{condition.right.value}%"
            elif "in" in condition.operator.value:
                operand_2 = [
                    d.lstrip().rstrip() for d in condition.right.value.split(",")
                ]
            elif "set" in condition.operator.value:
                operand_2 = None
            else:
                operand_2 = condition.right.value

        operation = Operations.get_operation(condition.operator.value)
        return operation(operand_1, operand_2)

    def process_limit(self):
        self._limit: int = self.limit or 10

    def convert_to_select_field(self, table, column) -> Field:
        table = Table(table)
        Field = table[column]

        # only add table to query if a column or filter from the table present
        if table not in self._tables:
            self._tables.append(table)

        return Field
