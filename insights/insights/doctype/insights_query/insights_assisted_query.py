# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe

from insights.insights.doctype.insights_data_source.sources.query_store import (
    sync_query_store,
)
from insights.utils import InsightsDataSource, InsightsQuery, InsightsTable

from .utils import (
    BaseNestedQueryImporter,
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

    def validate_if_all_column_tables_are_selected(self):
        columns = self.query_json.get_columns()
        tables = self.query_json.get_tables()
        for column in columns:
            if not column.is_valid() or column.is_expression() or column.get("column") == "count":
                continue
            if column.get("table") not in tables:
                frappe.throw(
                    msg=f"Table {column.get('table')} for column {column.get('label')} not selected. Add the table to the query and try again.",
                    title="Missing Column Table",
                )

    def before_save(self):
        update_sql(self.doc)
        self.doc.json = frappe.as_json(self.query_json)

    @property
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
        update_sql(self.doc)
        self.validate_if_all_column_tables_are_selected()
        if self.doc.data_source != "Query Store":
            return
        sub_queries = [
            t.get("table") for t in self.get_selected_tables() if t.get("table") != self.doc.name
        ]
        sync_query_store(sub_queries)

    def after_fetch(self, results):
        if not self.has_cumulative_columns():
            return results

        columns = [
            col
            for col in self.query_json.get_columns()
            if col.aggregation and "cumulative" in col.aggregation.lower()
        ]
        return apply_cumulative_sum(columns, results)

    def has_cumulative_columns(self):
        return any(
            col.aggregation and "cumulative" in col.aggregation.lower()
            for col in self.query_json.get_columns()
        )

    def fetch_results(self, additional_filters=None):
        query = self.doc
        if additional_filters:
            query = self.apply_additional_filters(additional_filters)
        return InsightsDataSource.get_doc(self.doc.data_source).run_query(query)

    def apply_additional_filters(self, additional_filters):
        query_json = self.query_json
        for filter in additional_filters:
            column = filter.get("column")
            value = filter.get("value")
            operator = filter.get("operator")
            query_json.add_filter(column, operator, value)
        self.doc.json = frappe.as_json(query_json)
        return self.doc

    def export_query(self):
        subqueries = frappe.get_all(
            "Insights Table",
            filters={
                "table": ["in", self.query_json.get_tables()],
                "is_query_based": 1,
            },
            pluck="table",
        )
        dependencies = {}
        for subquery in subqueries:
            if subquery in dependencies:
                continue
            query = InsightsQuery.get_doc(subquery)
            dependencies[query.name] = frappe.parse_json(query.export())

        return {"query": self.query_json, "subqueries": dependencies}

    def import_query(self, exported_query):
        return AssistedQueryImporter(exported_query, self.doc).import_query()


class AssistedQueryImporter(BaseNestedQueryImporter):
    def _update_doc(self):
        self.doc.json = frappe.as_json(self.data.query)

    def _update_subquery_references(self):
        for old_name, new_name in self.imported_queries.items():
            self._rename_subquery_in_table(old_name, new_name)
            self._rename_subquery_in_joins(old_name, new_name)
            self._rename_subquery_in_columns(old_name, new_name)
            self._rename_subquery_in_filters(old_name, new_name)
            self._rename_subquery_in_calculations(old_name, new_name)
            self._rename_subquery_in_measures(old_name, new_name)
            self._rename_subquery_in_dimensions(old_name, new_name)
            self._rename_subquery_in_orders(old_name, new_name)

    def _rename_subquery_in_table(self, old_name, new_name):
        if self.data.query["table"]["table"] == old_name:
            self.data.query["table"]["table"] = new_name

    def _rename_subquery_in_joins(self, old_name, new_name):
        for join in self.data.query["joins"]:
            if join["left_table"]["table"] == old_name:
                join["left_table"]["table"] = new_name
            if join["right_table"]["table"] == old_name:
                join["right_table"]["table"] = new_name
            if join["left_column"]["table"] == old_name:
                join["left_column"]["table"] = new_name
            if join["right_column"]["table"] == old_name:
                join["right_column"]["table"] = new_name

    def _rename_subquery_in_columns(self, old_name, new_name):
        for column in self.data.query["columns"]:
            if column["table"] == old_name:
                column["table"] = new_name

    def _rename_subquery_in_filters(self, old_name, new_name):
        for filter in self.data.query["filters"]:
            if filter["column"]["table"] == old_name:
                filter["column"]["table"] = new_name

    def _rename_subquery_in_calculations(self, old_name, new_name):
        for calculation in self.data.query["calculations"]:
            if calculation["table"] == old_name:
                calculation["table"] = new_name

    def _rename_subquery_in_measures(self, old_name, new_name):
        for measure in self.data.query["measures"]:
            if measure["table"] == old_name:
                measure["table"] = new_name

    def _rename_subquery_in_dimensions(self, old_name, new_name):
        for dimension in self.data.query["dimensions"]:
            if dimension["table"] == old_name:
                dimension["table"] = new_name

    def _rename_subquery_in_orders(self, old_name, new_name):
        for order in self.data.query["orders"]:
            if order["table"] == old_name:
                order["table"] = new_name
