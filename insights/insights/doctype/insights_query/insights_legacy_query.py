# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from copy import deepcopy
from json import dumps

import frappe
from frappe.utils.data import cstr

from insights.api.data_sources import fetch_column_values, get_tables
from insights.utils import InsightsDataSource, InsightsQuery, InsightsTable

from ..insights_data_source.sources.query_store import sync_query_store
from .insights_legacy_query_utils import (
    convert_into_simple_filter,
    convert_to_expression,
)
from .utils import (
    BaseNestedQueryImporter,
    apply_cumulative_sum,
    get_columns_with_inferred_types,
    update_sql,
)

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


class InsightsLegacyQueryClient:
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
            "is_expression": column.get("is_expression"),
            "expression": dumps(column.get("expression"), indent=2),
            "format_option": dumps(column.get("format_option"), indent=2),
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
                row.type = column.get("type")
                row.label = column.get("label")
                row.table = column.get("table")
                row.column = column.get("column")
                row.order_by = column.get("order_by")
                row.aggregation = column.get("aggregation")
                row.table_label = column.get("table_label")
                row.aggregation_condition = column.get("aggregation_condition")
                format_option = column.get("format_option")
                if format_option:
                    # check if format option is an object
                    row.format_option = (
                        dumps(format_option, indent=2)
                        if isinstance(format_option, dict)
                        else format_option
                    )
                expression = column.get("expression")
                if expression:
                    # check if expression is an object
                    row.expression = (
                        dumps(expression, indent=2) if isinstance(expression, dict) else expression
                    )
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
    def fetch_tables(self):
        with_query_tables = frappe.db.get_single_value("Insights Settings", "allow_subquery")
        return get_tables(self.data_source, with_query_tables)

    @frappe.whitelist()
    def fetch_columns(self):
        return self.variant_controller.get_tables_columns()

    @frappe.whitelist()
    def fetch_column_values(self, column, search_text=None):
        return fetch_column_values(
            column.get("data_source") or self.data_source,
            column.get("table"),
            column.get("column"),
            search_text,
        )

    @frappe.whitelist()
    def fetch_join_options(self, left_table, right_table):
        left_doc = frappe.get_cached_doc(
            "Insights Table",
            {
                "table": left_table,
                "data_source": self.data_source,
            },
        )
        right_doc = frappe.get_cached_doc(
            "Insights Table",
            {
                "table": right_table,
                "data_source": self.data_source,
            },
        )

        links = []
        for link in left_doc.table_links:
            if link.foreign_table == right_table:
                links.append(
                    frappe._dict(
                        {
                            "left": link.primary_key,
                            "right": link.foreign_key,
                        }
                    )
                )

        return {
            "left_columns": left_doc.get_columns(),
            "right_columns": right_doc.get_columns(),
            "saved_links": links,
        }


class InsightsLegacyQueryValidation:
    def validate(self):
        self.validate_tables()
        self.validate_limit()
        self.validate_filters()
        self.validate_columns()

    def validate_tables(self):
        tables = [row.table for row in self.doc.tables]
        tables = frappe.get_all(
            "Insights Table",
            filters={"name": ("in", tables)},
            fields=["table", "data_source", "hidden"],
        )
        for table in tables:
            if table.hidden:
                frappe.throw(f"Table {table.table} is hidden. You cannot query it")
            if table.data_source != self.doc.data_source:
                frappe.throw(f"Table {table.table} is not in the same data source")

    def validate_limit(self):
        if self.doc.limit and self.doc.limit < 1:
            frappe.throw("Limit must be greater than 0")

    def validate_filters(self):
        if not self.doc.filters:
            self.filters = DEFAULT_FILTERS

    def validate_columns(self):
        if frappe.flags.in_test:
            return
        # check if no duplicate labelled columns
        labels = []
        for row in self.doc.columns:
            if row.label and row.label in labels:
                frappe.throw(f"Duplicate Column {row.label}")
            labels.append(row.label)


class InsightsLegacyQueryController(InsightsLegacyQueryValidation):
    def __init__(self, doc):
        self.doc = doc

    def before_save(self):
        update_sql(self.doc)

    def after_reset(self):
        self.doc.filters = DEFAULT_FILTERS

    def get_columns_from_results(self, results):
        if not results:
            return []

        query_columns = self.doc.columns
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
                column_matches = qc.get("column") == result_column.get("label")
                if not label_matches and not column_matches:
                    continue
                result_column["format_options"] = qc.get("format_option")
                result_column["type"] = qc.get("type")
                break
            return frappe._dict(result_column)

        result_columns = results[0]
        return [add_format_options(rc) for rc in result_columns]

    def get_tables_columns(self):
        columns = []
        selected_tables = self.get_selected_tables()
        for table in selected_tables:
            table_doc = InsightsTable.get_doc(
                data_source=self.doc.data_source,
                table=table.table,
            )
            table_columns = table_doc.get_columns()
            columns += [
                frappe._dict(
                    {
                        "data_source": self.doc.data_source,
                        "table_label": table.get("label"),
                        "table": table.get("table"),
                        "column": c.get("column"),
                        "label": c.get("label"),
                        "type": c.get("type"),
                    }
                )
                for c in table_columns
            ]
        return columns

    def get_selected_tables(self):
        join_tables = []
        for table in self.doc.tables:
            if table.join:
                join = frappe.parse_json(table.join)
                join_tables.append(
                    frappe._dict(
                        table=join.get("with").get("value"),
                        label=join.get("with").get("label"),
                    )
                )

        return self.doc.tables + join_tables

    def before_fetch(self):
        if self.doc.data_source != "Query Store":
            return
        sub_stored_queries = [
            t.table for t in self.get_selected_tables() if t.table != self.doc.name
        ]
        sync_query_store(sub_stored_queries)

    def after_fetch(self, results):
        if not self.has_cumulative_columns():
            return results

        columns = [
            col for col in self.doc.columns if col.aggregation and "Cumulative" in col.aggregation
        ]
        return apply_cumulative_sum(columns, results)

    def has_cumulative_columns(self):
        return any(col.aggregation and "Cumulative" in col.aggregation for col in self.doc.columns)

    def fetch_results(self, additional_filters=None):
        query = self.doc
        if additional_filters:
            query = self.apply_additional_filters(additional_filters)
        return InsightsDataSource.get_doc(self.doc.data_source).run_query(query)

    def apply_additional_filters(self, additional_filters):
        filter_conditions = []
        for chart_filter in additional_filters:
            chart_filter = frappe._dict(chart_filter)
            filter_conditions.append(
                convert_to_expression(
                    chart_filter.column.get("table"),
                    chart_filter.column.get("column"),
                    chart_filter.operator,
                    chart_filter.value,
                    chart_filter.column_type,
                )
            )

        filters = frappe.parse_json(self.doc.filters)
        new_filters = frappe.parse_json(self.doc.filters)

        for new_filter in filter_conditions:
            found = False
            # TODO: FIX: additional_filters was simple filter, got converted to expression, then again converted to simple filter
            if new_simple_filter := convert_into_simple_filter(new_filter):
                for index, exisiting_filter in enumerate(filters.conditions):
                    existing_simple_filter = convert_into_simple_filter(exisiting_filter)
                    if not existing_simple_filter:
                        continue
                    if existing_simple_filter["column"] == new_simple_filter["column"]:
                        new_filters.conditions[index] = new_filter
                        found = True
                        break
            if not found:
                new_filters.conditions.append(new_filter)

        self.doc.filters = dumps(new_filters, indent=2)
        return self.doc

    def export_query(self):
        selected_tables = self.get_selected_tables()
        selected_table_names = [table.table for table in selected_tables]
        subqueries = frappe.get_all(
            "Insights Table",
            filters={
                "table": ["in", selected_table_names],
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

        query_dict = self.doc.as_dict()
        return {
            "query": {
                "tables": query_dict["tables"],
                "columns": query_dict["columns"],
                "filters": query_dict["filters"],
                "limit": query_dict["limit"],
            },
            "subqueries": dependencies,
        }

    def import_query(self, exported_query):
        return LegacyQueryImporter(exported_query, self.doc).import_query()


class LegacyQueryImporter(BaseNestedQueryImporter):
    def _update_doc(self):
        self.doc.set("tables", self.data.query["tables"])
        self.doc.set("columns", self.data.query["columns"])
        self.doc.set("filters", self.data.query["filters"])
        self.doc.set("limit", self.data.query["limit"])

    def _update_subquery_references(self):
        for old_name, new_name in self.imported_queries.items():
            self._rename_subquery_in_table(old_name, new_name)
            self._rename_subquery_in_joins(old_name, new_name)
            self._rename_subquery_in_columns(old_name, new_name)
            self._rename_subquery_in_filters(old_name, new_name)

    def _rename_subquery_in_table(self, old_name, new_name):
        for table in self.data.query["tables"]:
            if table["table"] == old_name:
                table["table"] = new_name

    def _rename_subquery_in_joins(self, old_name, new_name):
        for table in self.data.query["tables"]:
            if not table["join"]:
                continue
            join = frappe.parse_json(table["join"])
            if join["with"]["value"] == old_name:
                join["with"]["value"] = new_name
                join["with"]["table"] = new_name
                table["join"] = dumps(join, indent=2)

    def _rename_subquery_in_columns(self, old_name, new_name):
        for column in self.data.query["columns"]:
            if column["table"] == old_name:
                column["table"] = new_name

    def _rename_subquery_in_filters(self, old_name, new_name):
        # do a hacky string replace for now
        self.data.query["filters"] = self.data.query["filters"].replace(old_name, new_name)
