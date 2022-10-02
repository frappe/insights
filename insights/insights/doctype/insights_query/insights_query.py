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

from insights.insights.doctype.insights_query.utils import (
    parse_query_expression,
    make_query_field,
    Aggregations,
    ColumnFormat,
)

from insights.insights.doctype.insights_query.insights_query_client import (
    InsightsQueryClient,
)


class InsightsQuery(InsightsQueryClient):
    DEFAULT_FILTERS = dumps(
        {
            "type": "LogicalExpression",
            "operator": "&&",
            "level": 1,
            "position": 1,
            "conditions": [],
        },
        indent=2,
    )

    def before_validate(self):
        self.from_query_store = frappe.db.get_value(
            "Insights Data Source", self.data_source, "is_query_store", cache=True
        )

    def validate(self):
        # TODO: validate if a column is an expression and aggregation is "group by"
        self.validate_tables()
        self.validate_limit()
        self.validate_filters()

    def validate_tables(self):
        for row in self.tables:
            if not row.table:
                frappe.throw(f"Row #{row.idx}: Table is required")

        tables = [row.table for row in self.tables]
        tables = frappe.get_all(
            "Insights Table",
            filters={"name": ("in", tables)},
            fields=["table", "data_source", "hidden"],
        )
        for table in tables:
            if table.hidden:
                frappe.throw(f"Table {table.table} is hidden. You cannot query it")
            if table.data_source != self.data_source:
                frappe.throw(f"Table {table.table} is not in the same data source")

    def validate_limit(self):
        if self.limit and self.limit < 1:
            frappe.throw("Limit must be greater than 0")
        if self.limit and self.limit > 1000:
            frappe.throw("Limit must be less than 1000")

    def validate_filters(self):
        if not self.filters:
            self.filters = self.DEFAULT_FILTERS

    def on_update(self):
        # create a query visualization if not exists
        visualizations = self.get_visualizations()
        if not visualizations:
            frappe.get_doc(
                {
                    "doctype": "Insights Query Chart",
                    "query": self.name,
                    "title": self.title,
                }
            ).insert()

        if not frappe.db.exists("Insights Table", {"table": self.name}):
            self.create_query_table()

        old_title = self.get("_doc_before_save") and self.get("_doc_before_save").title
        if old_title and old_title != self.title:
            self.update_title()

    def on_trash(self):
        visualizations = self.get_visualizations()
        for visualization in visualizations:
            frappe.delete_doc("Insights Query Chart", visualization)

        if table_name := frappe.db.exists("Insights Table", {"table": self.name}):
            frappe.delete_doc("Insights Table", table_name)

    def clear(self):
        self.tables = []
        self.columns = []
        self.filters = self.DEFAULT_FILTERS
        self.sql = None
        self.result = None
        self.limit = 10
        self.execution_time = 0
        self.last_execution = None
        self.transform_type = None
        self.transform_data = None
        self.transform_result = None
        self.status = "Execution Successful"

    def before_save(self):
        if self.get("skip_before_save"):
            return

        if not self.tables:
            self.clear()
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

        if not self._columns and self.tables:
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
        if self.from_query_store:
            start, end, data = self.fetch_results_from_query_store()
        else:
            start, end, data = self.fetch_results_from_datasource()

        self._result = list(data)
        self.execution_time = flt(end - start, 3)
        self.last_execution = frappe.utils.now()
        self.result = dumps(self._result, default=cstr)
        self.status = "Execution Successful"

        self.update_query_table()

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
        self._columns = []
        self._group_by_columns = []
        self._order_by_columns = []

        for row in self.columns:
            if not row.is_expression:
                _column = self.process_dimension_or_metric(row)
            else:
                expression = loads(row.expression)
                _column = parse_query_expression(expression.get("ast"))
                _column = self.process_column_format(row, _column)

            self.process_sorting(row, _column)
            _column = _column.as_(row.label) if row.label else _column
            if row.aggregation == "Group By":
                self._group_by_columns.append(_column)

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
        if not row.aggregation or row.aggregation == "Group By":
            return column

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

    def build_temporary_table(self):
        columns = ["ID INT PRIMARY KEY"]
        rows = []

        mysql_type_map = {
            "Time": "TIME",
            "Date": "DATE",
            "String": "VARCHAR(255)",
            "Integer": "INT",
            "Decimal": "FLOAT",
            "Datetime": "DATETIME",
            "Text": "TEXT",
        }

        for row in self.columns:
            columns.append(
                f"`{row.column or row.label}` {mysql_type_map.get(row.type, 'VARCHAR(255)')}"
            )

        result = loads(self.result)
        for i, row in enumerate(result):
            rows.append([i] + list(row))

        create_table = f"CREATE TEMPORARY TABLE `{self.name}`({', '.join(columns)})"
        insert_records = (
            f"INSERT INTO `{self.name}` VALUES {', '.join(['%s'] * len(rows))}"
        )

        frappe.db.sql(create_table)
        # since "create temporary table" doesn't count as a write
        # to avoid "implicit commit" error
        frappe.db.transaction_writes -= 1
        frappe.db.sql(insert_records, values=rows)

    def fetch_results_from_datasource(self):
        data_source = frappe.get_cached_doc("Insights Data Source", self.data_source)
        start = time.time()
        data = data_source.execute_query(self.sql)
        end = time.time()
        return start, end, data

    def fetch_results_from_query_store(self):
        for row in self.get_selected_tables():
            # TODO: validate table is a valid query and not a database table
            frappe.get_doc("Insights Query", row.table).build_temporary_table()

        start = time.time()
        data = frappe.db.sql(self.sql)
        end = time.time()
        return start, end, data

    def update_query_table(self):
        if not self.tables:
            return

        table = self.get_query_table()
        old_columns = [(row.column, row.label, row.type) for row in table.columns]

        updated_columns = [("ID", "ID", "Integer")]
        if not self.columns:
            updated_columns += [
                (row.column or row.label, row.label, row.type)
                for row in self.fetch_columns()
            ]
        else:
            updated_columns += [
                (row.column or row.label, row.label, row.type) for row in self.columns
            ]

        if old_columns != updated_columns:
            table.set(
                "columns",
                [
                    {
                        "column": row[0],
                        "label": row[1],
                        "type": row[2],
                    }
                    for row in updated_columns
                ],
            )
            table.save()

    def get_query_table(self):
        if not frappe.db.exists("Insights Table", {"table": self.name}):
            return self.create_query_table()
        else:
            return frappe.get_doc("Insights Table", {"table": self.name})

    def create_query_table(self):
        table = frappe.get_doc(
            {
                "doctype": "Insights Table",
                "table": self.name,
                "data_source": "Query Store",
                "label": self.title,
                "columns": [
                    {
                        "column": "ID",
                        "label": "ID",
                        "type": "Integer",
                    }
                ],
            }
        )
        table.insert(ignore_permissions=True)
        return table

    def update_title(self):
        Chart = frappe.qb.DocType("Insights Query Chart")
        frappe.qb.update(Chart).set(Chart.title, self.title).where(
            Chart.query == self.name
        ).run()

        # this still doesn't updates the old title stored the query column
        Table = frappe.qb.DocType("Insights Table")
        frappe.qb.update(Table).set(Table.label, self.title).where(
            Table.table == self.name
        ).run()
