# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from functools import cached_property
from json import dumps

import frappe
from frappe.model.document import Document
from frappe.utils import cstr, flt
from sqlparse import format as format_sql

from ..insights_data_source.sources.query_store import sync_query_store
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
        self.validate_columns()

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

    def validate_columns(self):
        if frappe.flags.in_test:
            return
        # check if no duplicate labelled columns
        labels = []
        for row in self.columns:
            if row.label and row.label in labels:
                frappe.throw(f"Duplicate Column {row.label}")
            labels.append(row.label)


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
        self.sync_query_store()
        self.update_link_docs_title()
        # TODO: update result columns on update

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

    def fetch_results(self):
        results = list(self._data_source.run_query(query=self))
        columns = [f"{c.label or c.column}::{c.type}" for c in self.get_columns()]
        results.insert(0, columns)
        if self.transforms:
            results = self.apply_transform(results)
        if self.has_cumulative_columns():
            results = self.apply_cumulative_sum(results)
        return results

    def build_and_execute(self):
        start = time.time()
        results = self.fetch_results()
        self.execution_time = flt(time.time() - start, 3)
        self.last_execution = frappe.utils.now()
        self.result = dumps(results, default=cstr)
        self.status = "Execution Successful"

    def run_with_filters(self, filter_conditions):
        filters = frappe.parse_json(self.filters)
        filters.conditions.extend(filter_conditions)
        self.filters = dumps(filters, indent=2)
        results = self.fetch_results()
        return results

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
        frappe.db.delete("Insights Dashboard Item", {"chart": self.name})

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

    def sync_query_store(self):
        if self.is_stored:
            sync_query_store(tables=[self.name], force=True)

    def get_columns(self):
        return self.columns or self.fetch_columns()

    def load_result(self):
        return frappe.parse_json(self.result)

    def apply_transform(self, results):
        from pandas import DataFrame

        for row in self.transforms:
            if row.type == "Pivot":
                result = frappe.parse_json(results)
                options = frappe.parse_json(row.options)

                pivot_column = next(
                    (c for c in self.columns if c.column == options.column), None
                )
                index_column = next(
                    (c for c in self.columns if c.column == options.index), None
                )
                value_column = next(
                    (c for c in self.columns if c.column == options.value), None
                )

                if not (pivot_column and index_column and value_column):
                    frappe.throw("Invalid Pivot Options")

                results_df = DataFrame(
                    result[1:], columns=[d.split("::")[0] for d in result[0]]
                )

                pivot_column_values = results_df[pivot_column.label]
                index_column_values = results_df[index_column.label]
                value_column_values = results_df[value_column.label]

                # make a dataframe for pivot table
                pivot_df = DataFrame(
                    {
                        index_column.label: index_column_values,
                        pivot_column.label: pivot_column_values,
                        value_column.label: value_column_values,
                    }
                )

                pivoted = pivot_df.pivot_table(
                    index=[pivot_df.columns[0]],
                    columns=[pivot_df.columns[1]],
                    values=[pivot_df.columns[2]],
                    aggfunc="sum",
                )

                pivoted.columns = pivoted.columns.droplevel(0)
                pivoted = pivoted.reset_index()
                pivoted.columns.name = None
                pivoted = pivoted.fillna(0)

                cols = pivoted.columns.to_list()
                cols = [f"{cols[0]}::{index_column.type}"] + [
                    f"{c}::{value_column.type}" for c in cols[1:]
                ]
                data = pivoted.values.tolist()

                return [cols] + data

    def has_cumulative_columns(self):
        return any(
            col.aggregation and "Cumulative" in col.aggregation
            for col in self.get_columns()
        )

    def apply_cumulative_sum(self, results):
        from pandas import DataFrame

        result = frappe.parse_json(results)
        results_df = DataFrame(
            result[1:], columns=[d.split("::")[0] for d in result[0]]
        )

        for column in self.columns:
            if "Cumulative" in column.aggregation:
                results_df[column.label] = results_df[column.label].cumsum()

        return [result[0]] + results_df.values.tolist()


def format_query(query):
    return format_sql(
        query,
        keyword_case="upper",
        reindent_aligned=True,
    )
