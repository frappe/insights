# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from json import dumps

import frappe
import sqlparse
from frappe.model.document import Document
from frappe.utils import flt

from insights.insights.doctype.insights_data_source.sources.utils import (
    create_insights_table,
)

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
        if not self.tables and not self.is_native_query:
            return self.clear()

        if self.get("skip_before_save"):
            return

        self.update_query()

        if self.is_native_query:
            self.parse_tables_and_columns()

    def on_update(self):
        self.update_insights_table()
        self.sync_query_store()
        self.update_link_docs_title()
        # TODO: update result columns on update

    def on_trash(self):
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
        if self.data_source == "Query Store":
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

    def clear(self):
        self.tables = []
        self.columns = []
        self.filters = DEFAULT_FILTERS
        self.sql = None
        self.limit = 500
        self.execution_time = 0
        self.last_execution = None
        frappe.cache().delete_value(f"insights_query|{self.name}")
        self.status = "Execution Successful"

    def sync_query_store(self):
        if self.is_stored:
            sync_query_store(tables=[self.name], force=True)

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
        return (
            self.columns
            or self.get("_parsed_columns")
            or self.parse_tables_and_columns()[1]
            or self.fetch_columns()
        )

    def get_tables(self):
        return (
            self.tables
            or self.get("_parsed_tables")
            or self.parse_tables_and_columns()[0]
        )

    def parse_tables_and_columns(self):
        if not self.is_native_query:
            return []

        if self.get("_parsed_tables") and self.get("_parsed_columns"):
            return [self._parsed_tables, self._parsed_columns]

        tokens = get_identifier_tokens(self.sql)
        tables = []
        columns = []
        for token in tokens:
            if token.get("identifier") in ["from", "join"]:
                insights_table = get_insights_table(token.get("name"))
                tables.append(
                    frappe._dict(
                        {
                            "table": insights_table.table,
                            "label": insights_table.label,
                        }
                    )
                )

        for token in tokens:
            if token.get("identifier") == "select":
                if token.get("name") == "*":
                    # in this case all columns are fetched by fetch_columns
                    continue

                if token.get("parent"):
                    table = next(
                        (
                            t
                            for t in tokens
                            if t.get("name") == token.get("parent")
                            or t.get("alias") == token.get("parent")
                        ),
                        None,
                    )
                else:
                    table = tables[0]

                if not table:
                    continue
                insights_table = get_insights_table(table.get("table"))
                insights_column = next(
                    (
                        c
                        for c in insights_table.columns
                        if c.column == token.get("name")
                    ),
                    None,
                )
                if not insights_column:
                    # frappe.throw("Column not found: {0}".format(token.get("name")))
                    continue

                columns.append(
                    frappe._dict(
                        {
                            "table": insights_table.table,
                            "table_label": insights_table.label,
                            "column": insights_column.column,
                            "label": token.get("alias") or insights_column.label,
                            "type": insights_column.type,
                        }
                    )
                )

        self._parsed_tables = tables
        self._parsed_columns = columns

        return [tables, columns]

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
    return sqlparse.format(
        query,
        keyword_case="upper",
        reindent_aligned=True,
    )


def get_identifier_tokens(query):
    formatted = sqlparse.format(query, reindent=True, keyword_case="upper")
    parsed = sqlparse.parse(formatted)
    tokens = []
    identifier = None
    for statement in parsed:
        for token in statement.tokens:
            if (
                token.ttype is sqlparse.tokens.Keyword
                and token.value.lower() in ["from", "join"]
            ) or (
                token.ttype is sqlparse.tokens.DML and token.value.lower() == "select"
            ):
                identifier = token.value.lower()

            if identifier and isinstance(token, sqlparse.sql.Identifier):
                tokens.append(
                    {
                        "name": token.get_real_name(),
                        "alias": token.get_alias(),
                        "parent": token.get_parent_name(),
                        "identifier": identifier,
                    }
                )
                identifier = None
            if identifier and isinstance(token, sqlparse.sql.IdentifierList):
                for item in token.get_identifiers():
                    tokens.append(
                        {
                            "name": item.get_real_name(),
                            "alias": item.get_alias(),
                            "parent": token.get_parent_name(),
                            "identifier": identifier,
                        }
                    )
                identifier = None

    return tokens


def get_insights_table(table_name):
    if not frappe.db.exists("Insights Table", {"table": table_name}):
        frappe.throw(f"Table {table_name} does not exist")
    return frappe.get_cached_doc("Insights Table", {"table": table_name})
