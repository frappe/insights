# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from functools import cached_property
import time
from json import dumps
from sqlparse import format as format_sql

import frappe
from frappe.model.document import Document
from frappe.utils import cstr, flt

from .insights_query_client import InsightsQueryClient


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


class InsightsQueryValidation:
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
            self.filters = DEFAULT_FILTERS


class InsightsQuery(InsightsQueryValidation, InsightsQueryClient, Document):
    def before_save(self):
        if self.get("skip_before_save"):
            return

        if not self.tables:
            self.clear()
            return

        self.update_query()

    def on_update(self):
        self.create_default_chart()
        self.store_in_query_store()
        self.update_link_docs_title()

    def on_trash(self):
        self.delete_linked_charts()
        self.delete_insights_table()

    @cached_property
    def _data_source(self):
        return frappe.get_doc("Insights Data Source", self.data_source)

    def update_query(self):
        query = self._data_source.build_query(query=self)
        query = format_query(query)
        if self.sql != query:
            self.sql = query
            self.status = "Pending Execution"

    def build_and_execute(self):
        start = time.time()
        self._result = self._data_source.run_query(query=self)
        self.execution_time = flt(time.time() - start, 3)
        self.last_execution = frappe.utils.now()
        self.executed = True
        self.store_result()

        self.update_query_table()

    def store_result(self):
        self.result = dumps(self._result, default=cstr)
        self.status = "Execution Successful"

    def create_default_chart(self):
        charts = self.get_charts()
        if not charts:
            frappe.get_doc(
                {
                    "doctype": "Insights Query Chart",
                    "query": self.name,
                    "title": self.title,
                }
            ).insert()

    def store_in_query_store(self):
        if not frappe.db.exists("Insights Table", {"table": self.name}):
            self.create_query_table()

    def update_link_docs_title(self):
        old_title = self.get("_doc_before_save") and self.get("_doc_before_save").title
        if old_title and old_title != self.title:
            Chart = frappe.qb.DocType("Insights Query Chart")
            frappe.qb.update(Chart).set(Chart.title, self.title).where(
                Chart.query == self.name
            ).run()

            # this still doesn't updates the old title stored the query column
            Table = frappe.qb.DocType("Insights Table")
            frappe.qb.update(Table).set(Table.label, self.title).where(
                Table.table == self.name
            ).run()

    def delete_linked_charts(self):
        charts = self.get_charts()
        for chart in charts:
            frappe.delete_doc("Insights Query Chart", chart)
        frappe.db.delete("Insights Dashboard Item", {"query_chart": self.name})

    def delete_insights_table(self):
        if table_name := frappe.db.exists("Insights Table", {"table": self.name}):
            frappe.delete_doc("Insights Table", table_name)

    def clear(self):
        self.tables = []
        self.columns = []
        self.filters = DEFAULT_FILTERS
        self.sql = None
        self.result = None
        self.limit = 10
        self.execution_time = 0
        self.last_execution = None
        self.transform_type = None
        self.transform_data = None
        self.transform_result = None
        self.status = "Execution Successful"

    def get_columns(self):
        return self.columns or self.fetch_columns()

    def load_result(self):
        return frappe.parse_json(self.result)

    def update_query_table(self):
        if not self.tables:
            return

        table = self.get_query_table()
        old_columns = [(row.column, row.label, row.type) for row in table.columns]

        updated_columns = [("TEMPID", "ID", "Integer")]
        if not self.columns:
            updated_columns += [
                (row.column or row.label, row.label, row.type or "String")
                for row in self.fetch_columns()
            ]
        else:
            updated_columns += [
                (row.column or row.label, row.label, row.type or "String")
                for row in self.columns
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
                "data_source": "Query Store",
                "table": self.name,
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


def format_query(query):
    return format_sql(
        query,
        keyword_case="upper",
        reindent_aligned=True,
    )
