# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from functools import cached_property
from json import dumps

import frappe
from frappe.model.document import Document
from frappe.utils import flt
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
        limit = (
            frappe.db.get_single_value("Insights Settings", "query_result_limit")
            or 10000
        )
        if self.limit and self.limit > limit:
            frappe.throw(f"Limit must be less than {limit}")

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

    @property
    def _data_source(self):
        return frappe.get_doc("Insights Data Source", self.data_source)

    @property
    def results(self) -> str:
        """Returns the 1000 rows of the query results"""
        try:
            if self.status != "Execution Successful":
                return frappe.as_json([self._result_columns])

            cached_results = self.load_results()
            if not cached_results or len(cached_results) == 1:  # only columns
                results = self.fetch_results()
                return frappe.as_json(results[:1000])

            return frappe.as_json(cached_results[:1000])
        except Exception as e:
            print("Error getting results", e)

    @property
    def results_row_count(self):
        return len(self.load_results())

    def update_query(self):
        query = self._data_source.build_query(query=self)
        query = format_query(query)
        if self.sql != query:
            self.sql = query
            self.status = "Pending Execution"

    @property
    def _result_columns(self):
        return [f"{c.label or c.column}::{c.type}" for c in self.get_columns()]

    def fetch_results(self):
        if self.data_source == "Query Store":
            self.sync_child_stored_queries()
        results = list(self._data_source.run_query(query=self))
        results.insert(0, self._result_columns)
        if self.transforms:
            results = self.apply_transform(results)
        if self.has_cumulative_columns():
            results = self.apply_cumulative_sum(results)
        self.store_results(results)
        return results

    def sync_child_stored_queries(self):
        sync_query_store(
            [row.table for row in self.tables if row.table != self.name], force=True
        )

    def build_and_execute(self):
        start = time.time()
        self.fetch_results()
        self.execution_time = flt(time.time() - start, 3)
        self.last_execution = frappe.utils.now()
        self.status = "Execution Successful"

    def store_results(self, results):
        frappe.cache().set_value(
            f"insights_query|{self.name}",
            frappe.as_json(results),
        )

    def load_results(self, fetch_if_not_exists=False):
        results = frappe.cache().get_value(f"insights_query|{self.name}")
        if not results and fetch_if_not_exists:
            results = self.fetch_results()
        if not results:
            return [self._result_columns]
        return frappe.parse_json(results)

    def create_default_chart(self):
        charts = self.get_charts()
        if not charts:
            frappe.get_doc(
                {
                    "doctype": "Insights Query Chart",
                    "query": self.name,
                    "title": self.title,
                }
            ).insert(ignore_permissions=True)

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
            frappe.delete_doc("Insights Query Chart", chart, ignore_permissions=True)
            frappe.db.delete("Insights Dashboard Item", {"chart": chart})

    def delete_insights_table(self):
        if table_name := frappe.db.exists("Insights Table", {"table": self.name}):
            frappe.delete_doc("Insights Table", table_name, ignore_permissions=True)

    def clear(self):
        self.tables = []
        self.columns = []
        self.filters = DEFAULT_FILTERS
        self.sql = None
        self.limit = 500
        self.execution_time = 0
        self.last_execution = None
        self.transform_type = None
        self.transform_data = None
        self.transform_result = None
        frappe.cache().delete_value(f"insights_query|{self.name}")
        self.status = "Execution Successful"

    def sync_query_store(self):
        if self.is_stored:
            sync_query_store(tables=[self.name], force=True)

    def get_columns(self):
        return self.columns or self.fetch_columns()

    def apply_transform(self, results):
        from pandas import DataFrame

        for row in self.transforms:
            if row.type == "Pivot":
                result = frappe.parse_json(results)
                options = frappe.parse_json(row.options)
                pivot_column = options.get("column")
                index_column = options.get("index")
                index_column_type = next(
                    (c.type for c in self.columns if c.label == index_column),
                    None,
                )
                value_column = options.get("value")
                value_column_type = next(
                    (c.type for c in self.columns if c.label == value_column),
                    None,
                )

                if not (pivot_column and index_column and value_column):
                    frappe.throw("Invalid Pivot Options")
                if pivot_column == index_column:
                    frappe.throw("Pivot Column and Index Column cannot be same")

                results_df = DataFrame(
                    result[1:], columns=[d.split("::")[0] for d in result[0]]
                )

                pivot_column_values = results_df[pivot_column]
                index_column_values = results_df[index_column]
                value_column_values = results_df[value_column]

                # make a dataframe for pivot table
                pivot_df = DataFrame(
                    {
                        index_column: index_column_values,
                        pivot_column: pivot_column_values,
                        value_column: value_column_values,
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
                cols = [f"{cols[0]}::{index_column_type}"] + [
                    f"{c}::{value_column_type}" for c in cols[1:]
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
