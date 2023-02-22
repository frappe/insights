# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from json import dumps

import frappe
from frappe.model.document import Document

from insights import notify
from insights.cache_utils import get_or_set_cache, make_digest
from insights.insights.doctype.insights_team.insights_team import (
    get_allowed_resources_for_user,
)

from .utils import convert_into_simple_filter, convert_to_expression, get_item_position

CACHE_NAMESPACE = "insights_dashboard"


class InsightsDashboard(Document):
    @property
    def cache_namespace(self):
        return f"{CACHE_NAMESPACE}|{self.name}"

    @frappe.whitelist()
    def clear_charts_cache(self):
        frappe.cache().delete_keys(f"*{self.cache_namespace}:*")
        notify(**{"type": "success", "title": "Cache Cleared"})

    @frappe.whitelist()
    def fetch_chart_data(self, item_id, query_name=None, filters=None):
        row = next((row for row in self.items if row.item_id == item_id), None)
        if not row and not query_name:
            return frappe.throw("Item not found")

        query_name = query_name or frappe.parse_json(row.options).query
        if not query_name:
            return frappe.throw("Query not found")

        if query_name not in get_allowed_resources_for_user("Insights Query"):
            frappe.throw("Not allowed", frappe.PermissionError)

        filter_conditions = []
        for chart_filter in filters:
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

        return self.run_query(query_name, additional_filters=filter_conditions)

    def run_query(self, query_name, additional_filters=None):
        def get_result():
            query = frappe.get_cached_doc("Insights Query", query_name)
            if not additional_filters:
                return query.fetch_results()

            filters = frappe.parse_json(query.filters)

            new_filters = frappe.parse_json(query.filters)
            for new_filter in additional_filters:
                found = False
                # TODO: FIX: additional_filters was simple filter, got converted to expression, then again converted to simple filter
                if new_simple_filter := convert_into_simple_filter(new_filter):
                    for index, exisiting_filter in enumerate(filters.conditions):
                        existing_simple_filter = convert_into_simple_filter(
                            exisiting_filter
                        )
                        if not existing_simple_filter:
                            continue
                        if (
                            existing_simple_filter["column"]
                            == new_simple_filter["column"]
                        ):
                            new_filters.conditions[index] = new_filter
                            found = True
                            break
                if not found:
                    new_filters.conditions.append(new_filter)

            query.filters = dumps(new_filters)
            return query.fetch_results()

        last_modified = frappe.db.get_value("Insights Query", query_name, "modified")
        key = make_digest(query_name, last_modified, additional_filters)
        key = f"{self.cache_namespace}:{key}"

        query_result_expiry = frappe.db.get_single_value(
            "Insights Settings", "query_result_expiry"
        )
        query_result_expiry_in_seconds = query_result_expiry * 60
        return get_or_set_cache(key, get_result, expiry=query_result_expiry_in_seconds)


@frappe.whitelist()
def get_queries_column(query_names):
    # TODO: handle permissions
    tables = {}
    for query in list(set(query_names)):
        # TODO: to further optimize, store the used tables in the query on save
        doc = frappe.get_cached_doc("Insights Query", query)
        for table in doc.get_selected_tables():
            tables[table.table] = table

    columns = []
    for table in tables.values():
        doc = frappe.get_cached_doc("Insights Table", {"table": table.table})
        _columns = doc.get_columns()
        for column in _columns:
            columns.append(
                {
                    "column": column.column,
                    "label": column.label,
                    "table": table.table,
                    "table_label": table.label,
                    "type": column.type,
                    "data_source": doc.data_source,
                }
            )

    return columns


@frappe.whitelist()
def get_query_columns(query):
    # TODO: handle permissions
    return frappe.get_cached_doc("Insights Query", query).fetch_columns()


@frappe.whitelist()
def fetch_column_values(column, search_text=None):
    data_source = frappe.get_doc("Insights Data Source", column.get("data_source"))
    return data_source.get_column_options(
        column.get("table"), column.get("column"), search_text
    )
