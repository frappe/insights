# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from copy import deepcopy
from json import dumps, loads

import frappe
from frappe import _dict
from frappe.model.document import Document
from frappe.query_builder import Criterion, Field, Table
from frappe.utils import cint, cstr, flt
from sqlparse import format as format_sql

from pypika import Order
from pypika.enums import JoinType

from insights.insights.doctype.query.utils import (
    get_date_range,
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
    def update_table(self, table):
        for row in self.tables:
            if row.get("name") != table.get("name"):
                continue

            if table.get("join"):
                row.join = dumps(
                    table.get("join"),
                    default=cstr,
                    indent=2,
                )
            else:
                row.join = ""

            self.save()
            return

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
                row.table = column.get("table")
                row.column = column.get("column")
                row.order_by = column.get("order_by")
                row.aggregation = column.get("aggregation")
                row.table_label = column.get("table_label")
                row.aggregation_condition = column.get("aggregation_condition")
                row.format_option = dumps(column.get("format_option"), indent=2)
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
    def fetch_tables(self):
        _tables = []
        if not self.tables:

            def get_all_tables():
                return frappe.get_all(
                    "Table",
                    filters={"data_source": self.data_source},
                    fields=["table", "label"],
                    debug=True,
                )

            _tables = frappe.cache().get_value(
                f"query_tables_{self.data_source}", get_all_tables
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
            _tables = query.run(as_dict=True)

        return _tables

    @frappe.whitelist()
    def fetch_columns(self):
        if not self.tables:
            return []

        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        columns = []
        join_tables = []
        for table in self.tables:
            if table.join:
                join = loads(table.join)
                join_tables.append(
                    {
                        "table": join.get("with").get("value"),
                        "label": join.get("with").get("label"),
                    }
                )

        for table in self.tables + join_tables:
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
    def fetch_column_values(self, column, search_text):
        data_source = frappe.get_cached_doc("Data Source", self.data_source)
        return data_source.get_distinct_column_values(column, search_text)

    @frappe.whitelist()
    def fetch_operator_list(self, fieldtype=None):
        operator_list = [
            {"label": "equals", "value": "="},
            {"label": "not equals", "value": "!="},
            {"label": "is", "value": "is"},
        ]

        if not fieldtype:
            return operator_list

        text_data_types = ("char", "varchar", "enum", "text", "longtext")
        number_data_types = ("int", "decimal", "bigint", "float", "double")
        date_data_types = ("date", "datetime", "time", "timestamp")

        fieldtype = fieldtype.lower()
        if fieldtype in text_data_types:
            operator_list += [
                {"label": "contains", "value": "contains"},
                {"label": "not contains", "value": "not contains"},
                {"label": "starts with", "value": "starts with"},
                {"label": "ends with", "value": "ends with"},
                {"label": "is one of", "value": "in"},
                {"label": "is not one of", "value": "not in"},
            ]
        if fieldtype in number_data_types:
            operator_list += [
                {"label": "is one of", "value": "in"},
                {"label": "is not one of", "value": "not in"},
                {"label": "greater than", "value": ">"},
                {"label": "smaller than", "value": "<"},
                {"label": "greater than equal to", "value": ">="},
                {"label": "smaller than equal to", "value": "<="},
                {"label": "between", "value": "between"},
            ]

        if fieldtype in date_data_types:
            operator_list += [
                {"label": "greater than", "value": ">"},
                {"label": "smaller than", "value": "<"},
                {"label": "greater than equal to", "value": ">="},
                {"label": "smaller than equal to", "value": "<="},
                {"label": "between", "value": "between"},
                {"label": "within", "value": "timespan"},
            ]

        return operator_list

    @frappe.whitelist()
    def fetch_join_options(self, table):
        doc = frappe.get_cached_doc(
            "Table",
            {
                "table": table.get("table"),
                "data_source": self.data_source,
            },
        )

        return [
            {
                "key": d.foreign_key,
                "table": d.foreign_table,
                "label": d.foreign_table_label,
            }
            for d in doc.get("table_links")
        ]

    @frappe.whitelist()
    def run(self):
        self.execute()
        self.update_result()

        # skip processing and updating query since it's already done
        self.skip_before_save = True
        self.save()

    @frappe.whitelist()
    def reset(self):
        self.tables = []
        self.columns = []
        self.filters = dumps(
            {
                "group_operator": "&",
                "level": "1",
                "position": "1",
                "conditions": [],
            },
            indent=2,
        )
        self.sql = None
        self.result = None
        self.status = "Pending Execution"
        self.limit = 10
        self.execution_time = 0
        self.last_execution = None
        self.transform_type = None
        self.transform_data = None
        self.transform_result = None
        self.skip_before_save = True

        self.save()

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

        query = query.where(*self._filters)

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
            _column = self.process_query_field(row.table, row.column)
            # dates should be formatted before aggregagtions
            _column = self.process_column_format(row, _column)
            _column = self.process_aggregation(row, _column)

            self.process_sorting(row, _column)
            _column = _column.as_(row.label)
            self._columns.append(_column)

    def process_column_format(self, row, column):
        if row.format_option and row.type in ("Date", "Datetime"):
            format_option = _dict(loads(row.format_option))
            return ColumnFormat.format_date(format_option.date_format, column)
        return column

    def process_aggregation(self, row, column):
        if not row.aggregation:
            return column

        if row.aggregation == "Count Distinct":
            column = Aggregations.apply("Distinct", column)
            column = Aggregations.apply("Count", column)

        elif row.aggregation == "Count if" and row.aggregation_condition:
            conditions = [
                self.process_expression(condition)
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
        if type(literal.value) == str:
            literal.value = literal.value.replace('"', "")

        if operator.value == "contains":
            return f"%{literal.value}%"

        if operator.value == "starts with":
            return f"{literal.value}%"

        if operator.value == "ends with":
            return f"%{literal.value}"

        if operator.value == "in":
            return [d.lstrip().rstrip() for d in literal.value]

        if operator.value == "between":
            return [d.lstrip().rstrip() for d in literal.value.split(",")]

        if operator.value == "timespan":
            timespan_value = literal.value.lower().strip()
            if "current" in timespan_value:
                return get_date_range(timespan=timespan_value)

            elif "last" in timespan_value:
                [span, interval, interval_type] = timespan_value.split(" ")
                timespan = span + " n " + interval_type
                return get_date_range(timespan=timespan, n=int(interval))

        return literal.value

    def process_limit(self):
        self._limit: int = self.limit or 10

    def process_query_field(self, table, column) -> Field:
        return Table(table)[column]
