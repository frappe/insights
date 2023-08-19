# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from functools import cached_property

import frappe

from insights.utils import InsightsDataSource, InsightsTable

from .utils import (
    Column,
    Query,
    apply_cumulative_sum,
    get_columns_with_inferred_types,
    update_sql,
)

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

    def before_save(self):
        update_sql(self.doc)
        self.doc.json = frappe.as_json(self.query_json)

    @cached_property
    def query_json(self):
        query = frappe.parse_json(self.doc.json)
        return Query(**query)

    def get_columns_from_results(self, results):
        if not results:
            return []

        query_columns = self.query_json.get_columns()
        inferred_column_types = get_columns_with_inferred_types(results)
        if not query_columns:
            return inferred_column_types

        def get_inferred_column_type(result_column):
            for ic in inferred_column_types:
                if ic.get("label") == result_column.get("label"):
                    return ic.get("type")
            return "String"

        def add_format_options(result_column):
            result_column["format_options"] = {}
            result_column["type"] = get_inferred_column_type(result_column)
            for qc in query_columns:
                label_matches = qc.get("label") == result_column.get("label")
                alias_matches = qc.get("alias") == result_column.get("label")
                if not label_matches and not alias_matches:
                    continue
                result_column["label"] = qc.get("alias") or qc.get("label")
                # temporary fix until we change format_options in result columns from dict to str
                result_column["format_options"] = {"date_format": qc.get("granularity")}
                result_column["type"] = qc.get("type")
                break
            return frappe._dict(result_column)

        result_columns = results[0]
        return [add_format_options(rc) for rc in result_columns]

    def get_tables_columns(self):
        columns = []
        selected_tables = self.get_selected_tables()
        selected_tables_names = [t.get("table") for t in selected_tables]
        for table in set(selected_tables_names):
            table_doc = InsightsTable.get_doc(data_source=self.doc.data_source, table=table)
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
        return

    def after_fetch(self, results):
        if not self.has_cumulative_columns():
            return results

        columns = [
            col
            for col in self.query_json.get_columns()
            if col.aggregation and "cumulative" in col.aggregation
        ]
        return apply_cumulative_sum(columns, results)

    def has_cumulative_columns(self):
        return any(
            col.aggregation and "cumulative" in col.aggregation
            for col in self.query_json.get_columns()
        )

    def fetch_results(self):
        return InsightsDataSource.get_doc(self.doc.data_source).run_query(self.doc)
