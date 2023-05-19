# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from functools import cached_property

import frappe

from .utils import Column, InsightsTable, Query, get_columns_with_inferred_types

DEFAULT_JSON = {
    "table": {},
    "joins": [],
    "columns": [],
    "calculations": [],
    "filters": [],
    "measures": [],
    "dimensions": [],
    "orders": [],
    "limit": None,
}


class InsightsAssistedQueryController:
    def __init__(self, doc):
        self.doc = doc

    def validate(self):
        if not frappe.parse_json(self.doc.json):
            self.doc.json = frappe.as_json(DEFAULT_JSON)

    @cached_property
    def query_json(self):
        query = frappe.parse_json(self.doc.json)
        query.columns = (c.get("column") for c in query.columns or [])
        query.calculations = (c.get("column") for c in query.calculations or [])
        query.measures = (c.get("column") for c in query.measures or [])
        query.dimensions = (c.get("column") for c in query.dimensions or [])
        query.orders = (c.get("column") for c in query.orders or [])
        return Query(**query)

    def get_sql(self):
        return self.doc._data_source.build_query(self.doc, with_cte=True)

    def get_columns(self):
        return self.get_columns_from_results(self.doc.retrieve_results())

    def get_columns_from_results(self, results):
        if not results:
            return []

        query_columns = self.query_json.get_columns()
        if not query_columns:
            # then its a select * query
            return get_columns_with_inferred_types(results)

        def find_query_column(label):
            for qc in query_columns:
                if qc.alias == label:
                    return qc

        result_columns = results[0]
        # find the query column to get the formatting options
        return [find_query_column(rc["label"]) for rc in result_columns]

    def get_tables_columns(self):
        columns = []
        selected_tables = self.get_selected_tables()
        selected_tables_names = [t.get("table") for t in selected_tables]
        for table in set(selected_tables_names):
            table_doc = InsightsTable.get_doc(
                data_source=self.doc.data_source, table=table
            )
            table_columns = table_doc.get_columns()
            columns += [
                frappe._dict(
                    {
                        **Column(**c.as_dict()),
                        "data_source": self.doc.data_source,
                        "table_label": table_doc.label,
                        "table": table_doc.table,
                    }
                )
                for c in table_columns
            ]
        return columns

    def get_selected_tables(self):
        if not self.query_json.table:
            return []
        tables = [self.query_json.table]
        join_tables = [join.right_table for join in self.query_json.joins]
        return tables + join_tables

    def before_fetch(self):
        if self.doc.data_source != "Query Store":
            return
        raise frappe.ValidationError(
            "Query Store data source is not supported for assisted query"
        )

    def after_fetch_results(self, results):
        return results
