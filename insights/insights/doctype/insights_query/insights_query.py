# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from json import dumps

import frappe
import pandas as pd
import sqlparse
from frappe.model.document import Document
from frappe.utils import flt

from insights.decorators import log_error
from insights.insights.doctype.insights_data_source.sources.utils import (
    create_insights_table,
)
from insights.utils import ResultColumn

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
        if not self.tables and not self.is_native_query:
            return self.clear()

        if self.get("skip_before_save"):
            return

        self.update_query()

    def on_update(self):
        self.create_chart()
        self.update_insights_table()
        self.sync_query_store()
        self.update_link_docs_title()
        # TODO: update result columns on update

    def create_chart(self):
        if not frappe.db.exists("Insights Chart", {"query": self.name}):
            chart = frappe.new_doc("Insights Chart")
            chart.query = self.name
            chart.save(ignore_permissions=True)

    def on_trash(self):
        self.delete_insights_table()
        self.delete_insights_charts()

    @property
    def _data_source(self):
        return frappe.get_doc("Insights Data Source", self.data_source)

    @property
    def results(self) -> str:
        LIMIT = (
            frappe.db.get_single_value("Insights Settings", "query_result_limit")
            or 1000
        )
        try:
            cached_results = self.load_results()
            if not cached_results and self.status == "Execution Successful":
                results = self.fetch_results()
                return frappe.as_json(results[:LIMIT])

            return frappe.as_json(cached_results[:LIMIT])
        except Exception as e:
            print("Error getting results", e)

    @property
    def results_row_count(self):
        return len(self.load_results() or [])

    def update_query(self):
        if not self.is_native_query:
            query = self._data_source.build_query(query=self, with_cte=True)
        else:
            query = self.sql
        query = format_query(query) if query else None
        if self.sql != query:
            self.sql = query
            self.status = "Pending Execution"

    def fetch_results(self):
        self.sync_child_stored_queries()
        start = time.monotonic()
        results = []
        try:
            results = self._data_source.run_query(query=self)
            results = self.process_column_types(results)
            results = self.apply_transformations(results)
            self.execution_time = flt(time.monotonic() - start, 3)
            self.last_execution = frappe.utils.now()
            self.status = "Execution Successful"
        except Exception:
            self.status = "Pending Execution"
            print("Error fetching results")
            raise

        self.store_results(results)
        return results

    def sync_child_stored_queries(self):
        if self.data_source == "Query Store" and self.tables:
            sync_query_store(
                [row.table for row in self.tables if row.table != self.name], force=True
            )

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
            return []
        return frappe.parse_json(results)

    def update_link_docs_title(self):
        old_title = self.get("_doc_before_save") and self.get("_doc_before_save").title
        if old_title and old_title != self.title:
            # this still doesn't updates the old title stored the query column
            Table = frappe.qb.DocType("Insights Table")
            frappe.qb.update(Table).set(Table.label, self.title).where(
                Table.table == self.name
            ).run()

    def delete_insights_table(self):
        if table_name := frappe.db.exists("Insights Table", {"table": self.name}):
            frappe.delete_doc("Insights Table", table_name, ignore_permissions=True)

    def delete_insights_charts(self):
        charts = frappe.get_all(
            "Insights Chart",
            filters={"query": self.name},
            fields=["name"],
        )
        for chart in charts:
            frappe.delete_doc("Insights Chart", chart.name, ignore_permissions=True)

    def clear(self):
        self.tables = []
        self.columns = []
        self.filters = DEFAULT_FILTERS
        self.sql = ""
        self.limit = 500
        self.execution_time = 0
        self.last_execution = None
        frappe.cache().delete_value(f"insights_query|{self.name}")
        self.status = "Execution Successful"

    def sync_query_store(self):
        if self.is_stored:
            sync_query_store(tables=[self.name], force=True)

    @log_error()
    def process_column_types(self, results):
        if not results:
            return results

        if not self.is_native_query:
            results[0] = [ResultColumn.make(query_column=c) for c in self.get_columns()]
            return results

        columns = results[0]
        rows_df = pd.DataFrame(results[1:], columns=[c["label"] for c in columns])
        # create a row that contains values in each column
        values_row = []
        for column in rows_df.columns:
            # find the first non-null value in the column
            value = rows_df[column].dropna().iloc[0]
            values_row.append(value)

        # infer the type of each column
        inferred_types = self.guess_types(values_row)
        # update the column types
        for i, column in enumerate(columns):
            columns[i] = ResultColumn.make(
                label=column["label"],
                type=inferred_types[i],
            )
        results[0] = columns
        return results

    def guess_types(self, values):
        # try converting each value to a number, float, date, datetime
        # if it fails, it's a string
        types = []
        for value in values:
            types.append(guess_type(value))
        return types

    def update_insights_table(self):
        create_insights_table(
            frappe._dict(
                {
                    "table": self.name,
                    "label": self.title,
                    "data_source": self.data_source,
                    "is_query_based": 1,
                    "columns": [
                        frappe._dict(
                            {
                                "column": column.label,  # use label as column name
                                "label": column.label,
                                "type": column.type,
                            }
                        )
                        for column in self.get_columns()
                    ],
                }
            )
        )

    def get_columns(self):
        if not self.is_native_query:
            return self.columns or self.fetch_columns()

        # make column from results first row
        results = self.load_results(fetch_if_not_exists=True)
        if not results:
            return []
        return [
            frappe._dict(
                {
                    "label": col["label"],
                    "type": col["type"],
                }
            )
            for col in results[0]
        ]

    def apply_transformations(self, results):
        if self.is_native_query:
            return results
        if self.transforms:
            results = self.apply_transform(results)
        if self.has_cumulative_columns():
            results = self.apply_cumulative_sum(results)
        return results

    def apply_transform(self, results):
        self.validate_transforms()

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
                index_column_options = next(
                    (c.format_option for c in self.columns if c.label == index_column),
                    None,
                )
                index_column_options = frappe.parse_json(index_column_options)
                value_column = options.get("value")
                value_column_type = next(
                    (c.type for c in self.columns if c.label == value_column),
                    None,
                )

                if not (pivot_column and index_column and value_column):
                    frappe.throw("Invalid Pivot Options")
                if pivot_column == index_column:
                    frappe.throw("Pivot Column and Index Column cannot be same")

                results_df = pd.DataFrame(
                    result[1:], columns=[d["label"] for d in result[0]]
                )

                pivot_column_values = results_df[pivot_column]
                index_column_values = results_df[index_column]
                value_column_values = results_df[value_column]

                # make a dataframe for pivot table
                pivot_df = pd.DataFrame(
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
                index_result_column = ResultColumn.make(
                    cols[0], index_column_type, index_column_options
                )
                other_columns = [
                    ResultColumn.make(c, value_column_type) for c in cols[1:]
                ]
                cols = [index_result_column] + other_columns
                data = pivoted.values.tolist()

                return [cols] + data

            if row.type == "Unpivot":
                options = frappe.parse_json(row.options)
                index_column = options.get("index_column")
                new_column_name = options.get("column_label")
                value_name = options.get("value_label")

                if not (index_column and new_column_name and value_name):
                    frappe.throw("Invalid Unpivot Options")

                result = frappe.parse_json(results)
                columns = [c["label"] for c in result[0]]
                results_df = pd.DataFrame(result[1:], columns=columns)

                unpivoted = pd.melt(
                    results_df,
                    id_vars=[index_column],
                    var_name=new_column_name,
                    value_name=value_name,
                )

                index_column_type = next(
                    (c.type for c in self.columns if c.label == index_column),
                    None,
                )
                index_column_options = next(
                    (c.format_option for c in self.columns if c.label == index_column),
                    None,
                )
                index_column_options = frappe.parse_json(index_column_options)
                new_column_type = "String"
                value_column_type = "Decimal"

                cols = unpivoted.columns.to_list()
                cols = [
                    ResultColumn.make(cols[0], index_column_type, index_column_options),
                    ResultColumn.make(cols[1], new_column_type),
                    ResultColumn.make(cols[2], value_column_type),
                ]

                data = unpivoted.values.tolist()

                return [cols] + data

            if row.type == "Transpose":

                options = frappe.parse_json(row.options)
                index_column = options.get("index_column")
                new_column_label = options.get("column_label")

                if not index_column:
                    frappe.throw("Invalid Transpose Options")

                result = frappe.parse_json(results)
                columns = [c["label"] for c in result[0]]
                results_df = pd.DataFrame(result[1:], columns=columns)
                results_df = results_df.set_index(index_column)
                results_df_transposed = results_df.transpose()
                results_df_transposed = results_df_transposed.reset_index()
                results_df_transposed.columns.name = None

                cols = results_df_transposed.columns.to_list()
                index_result_column = ResultColumn.make(new_column_label, "String")
                other_columns = [ResultColumn.make(c, "Decimal") for c in cols[1:]]
                cols = [index_result_column] + other_columns
                data = results_df_transposed.values.tolist()

                return [cols] + data

    def validate_transforms(self):
        pivot_transforms = [t for t in self.transforms if t.type == "Pivot"]
        unpivot_transforms = [t for t in self.transforms if t.type == "Unpivot"]
        transpose_transforms = [t for t in self.transforms if t.type == "Transpose"]

        if len(pivot_transforms) > 1:
            frappe.throw("Only one Pivot transform is allowed")
        if len(unpivot_transforms) > 1:
            frappe.throw("Only one Unpivot transform is allowed")
        if len(transpose_transforms) > 1:
            frappe.throw("Only one Transpose transform is allowed")
        if pivot_transforms and unpivot_transforms:
            frappe.throw("Pivot and Unpivot transforms cannot be used together")
        if pivot_transforms and transpose_transforms:
            frappe.throw("Pivot and Transpose transforms cannot be used together")
        if unpivot_transforms and transpose_transforms:
            frappe.throw("Unpivot and Transpose transforms cannot be used together")

    def has_cumulative_columns(self):
        return any(
            col.aggregation and "Cumulative" in col.aggregation
            for col in self.get_columns()
        )

    def apply_cumulative_sum(self, results):
        result = frappe.parse_json(results)
        results_df = pd.DataFrame(result[1:], columns=[d["label"] for d in result[0]])

        for column in self.columns:
            if "Cumulative" in column.aggregation:
                results_df[column.label] = results_df[column.label].cumsum()

        return [result[0]] + results_df.values.tolist()


def format_query(query):
    return sqlparse.format(
        str(query),
        keyword_case="upper",
        reindent_aligned=True,
    )


def guess_type(value):
    try:
        pd.to_numeric(value)
        return "Integer"
    except ValueError:
        try:
            pd.to_numeric(value, downcast="float")
            return "Decimal"
        except ValueError:
            try:
                pd.to_datetime(value)
                return "Datetime"
            except ValueError:
                return "String"
