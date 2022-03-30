# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from json import dumps, loads

import frappe
from frappe import _dict
from frappe.model.document import Document
from frappe.query_builder import Criterion, Field, Table
from frappe.utils import cstr
from sqlparse import format as format_sql

from analytics.analytics.doctype.query.utils import AGGREGATIONS, Operations


class Query(Document):
    def validate(self):
        # TODO: validate if a column is an expression and aggregation is "group by"
        pass

    @frappe.whitelist()
    def update_tables(self, updated_tables):
        # remove the tables from self.tables if not present in updated_tables
        table_names = [row.get("label") for row in updated_tables]
        for table in [d for d in self.tables if d.get("table") not in table_names]:
            self.remove(table)

        # add the tables to self.tables if not already present
        table_names = [row.table for row in self.tables]
        for row in [d for d in updated_tables if d.get("label") not in table_names]:
            self.append(
                "tables",
                {
                    "table": row.get("table"),
                    "label": row.get("label"),
                },
            )

        self.save()

    @frappe.whitelist()
    def update_columns(self, updated_columns):
        # remove the columns from self.columns if not present in updated_columns
        column_names = [row.get("column") for row in updated_columns]
        for row in [d for d in self.columns if d.get("column") not in column_names]:
            self.remove(row)

        # add the columns to self.columns if not already present
        column_names = [row.column for row in self.columns]
        for row in [d for d in updated_columns if d.get("column") not in column_names]:
            self.append(
                "columns",
                {
                    "type": row.get("type"),
                    "label": row.get("label"),
                    "table": row.get("table"),
                    "column": row.get("column"),
                    "table_label": row.get("table_label"),
                    "aggregation": row.get("aggregation"),
                },
            )

        # update all aggregations
        aggregations = {
            row.get("column"): row.get("aggregation") for row in updated_columns
        }

        for row in self.columns:
            if row.get("column") in aggregations:
                row.aggregation = aggregations[row.get("column")]

        self.save()

    @frappe.whitelist()
    def update_filters(self, updated_filters):
        self.filters = dumps(updated_filters, indent=2, default=str)
        self.save()

    @frappe.whitelist()
    def get_selectable_tables(self):
        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        return data_source.get_tables()

    @frappe.whitelist()
    def get_selectable_columns(self, tables):
        tables = frappe.parse_json(tables)
        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        columns = []
        for table in tables:
            columns += data_source.get_columns(table)
        return columns

    def before_save(self):
        if not self.tables or not self.columns or not self.filters:
            self.result = "[]"
            return

        self.process()
        self.build()
        self.execute()
        self.sql = format_sql(
            str(self._query), keyword_case="upper", reindent_aligned=True
        )
        self.result = dumps(self._result, default=cstr)

    def process(self):
        self.process_tables()
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

        query = query.where(*self._filters)

        query = query.limit(self._limit)

        self._query = query

    def execute(self):
        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        self._result = data_source.execute(self._query, debug=True)
        self._result = list(self._result)
        self.format_result()

    def process_tables(self):
        self._tables = []
        for row in self.tables:
            table = Table(row.get("table"))
            self._tables.append(table)

    def process_columns(self):
        self._columns = []
        self._group_by_columns = []

        for row in self.columns:
            _column = self.convert_to_select_field(
                row.table, row.column, row.label, row.aggregation
            )

            if row.aggregation and row.aggregation == "Group By":
                self._group_by_columns.append(_column)

            self._columns.append(_column)

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
            condition.left.table, condition.left.column, condition.left.label
        )
        if condition.right.value_type == "Column":
            operand_2 = self.convert_to_select_field(
                condition.right.table, condition.right.column, condition.right.label
            )
        else:
            operand_2 = condition.right.value

        operation = Operations.get_operation(condition.operator.value)
        return operation(operand_1, operand_2)

    def process_limit(self):
        self._limit: int = self.limit or 10

    def convert_to_select_field(self, table, column, label, aggregation="") -> Field:
        table = Table(table)
        Field = table[column]
        Field = Field.as_(label)

        if aggregation and aggregation != "Group By":
            aggregation = AGGREGATIONS[aggregation]
            Field = aggregation(Field)

        return Field

    def format_result(self):
        column_names = [d.alias or d.name for d in self._columns]
        self._result.insert(0, column_names)
