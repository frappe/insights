# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import random
from contextlib import suppress
from json import dumps

import frappe
from frappe.model.document import Document

from insights import notify
from insights.api.permissions import is_private
from insights.api.telemetry import track
from insights.cache_utils import make_digest

from .utils import guess_layout_for_chart

CACHE_NAMESPACE = "insights_dashboard"


class InsightsDashboard(Document):
    def on_trash(self):
        track("delete_dashboard")

    @frappe.whitelist()
    def is_private(self):
        return is_private("Insights Dashboard", self.name)

    @property
    def cache_namespace(self):
        return f"{CACHE_NAMESPACE}|{self.name}"

    def add_chart(self, chart):
        chart_doc = frappe.get_doc("Insights Chart", chart)
        new_layout = guess_layout_for_chart(chart_doc.chart_type, self)
        self.append(
            "items",
            {
                "item_id": frappe.utils.cint(random.random() * 1000000),
                "item_type": chart_doc.chart_type,
                "options": chart_doc.options,
                "layout": new_layout,
            },
        )
        self.save()

    @frappe.whitelist()
    def clear_charts_cache(self):
        frappe.cache().delete_keys(f"*{self.cache_namespace}:*")
        for row in self.items:
            if '"query"' not in row.options:
                continue
            options = frappe.parse_json(row.options)
            if not options.query:
                continue
            frappe.cache().delete_keys(f"*insights_query_results:{options.query}*")
        notify(**{"type": "success", "title": "Cache Cleared"})

    @frappe.whitelist()
    def fetch_chart_data(self, item_id, query_name=None, filters=None):
        row = next((row for row in self.items if row.item_id == item_id), None)
        if not row and not query_name:
            return frappe.throw("Item not found")

        query_name = query_name or frappe.parse_json(row.options).query
        if not query_name:
            return frappe.throw("Query not found")

        return self.run_query(query_name, additional_filters=filters)

    def run_query(self, query_name, additional_filters=None):
        last_modified = frappe.db.get_value("Insights Query", query_name, "modified")
        key = make_digest(query_name, last_modified, additional_filters)
        key = f"{self.cache_namespace}:{key}"
        if frappe.cache().exists(key):
            return frappe.cache().get_value(key)

        query = frappe.get_cached_doc("Insights Query", query_name)
        # TODO: if 3 charts with same query results is fetched, it will be fetched 3 times
        new_results = query.fetch_results(additional_filters=additional_filters)

        query_result_expiry = frappe.db.get_single_value(
            "Insights Settings", "query_result_expiry"
        )
        query_result_expiry_in_seconds = query_result_expiry * 60
        frappe.cache().set_value(key, new_results, expires_in_sec=query_result_expiry_in_seconds)
        return new_results


@frappe.whitelist()
def get_queries_column(query_names):
    # TODO: handle permissions
    table_by_datasource = {}
    for query_name in list(set(query_names)):
        # TODO: to further optimize, store the used tables in the query on save
        query = frappe.get_cached_doc("Insights Query", query_name)
        for table in query.get_selected_tables():
            if query.data_source not in table_by_datasource:
                table_by_datasource[query.data_source] = {}
            table_by_datasource[query.data_source][table.table] = table

    columns = []
    for data_source, tables in table_by_datasource.items():
        for table_name, table in tables.items():
            table_doc = None
            with suppress(frappe.DoesNotExistError):
                table_doc = frappe.get_cached_doc(
                    "Insights Table",
                    {
                        "table": table_name,
                        "data_source": data_source,
                    },
                )

            if not table_doc:
                continue

            _columns = table_doc.get_columns()
            for column in _columns:
                columns.append(
                    {
                        "column": column.column,
                        "label": column.label,
                        "table": table.table,
                        "table_label": table.label,
                        "type": column.type,
                        "data_source": data_source,
                    }
                )

    return columns


@frappe.whitelist()
def get_query_columns(query):
    # TODO: handle permissions
    return frappe.get_cached_doc("Insights Query", query).fetch_columns()


def get_dashboard_public_key(name):
    existing_key = frappe.db.get_value("Insights Dashboard", name, "public_key", cache=True)
    if existing_key:
        return existing_key

    public_key = frappe.generate_hash()
    frappe.db.set_value("Insights Dashboard", name, "public_key", public_key)
    return public_key


@frappe.whitelist()
def get_dashboard_file(filename):
    file = frappe.get_doc("File", filename)
    dashboard = file.get_content()
    dashboard = frappe.parse_json(dashboard)
    queries = [frappe.parse_json(query) for query in dashboard.get("queries").values()]
    data_sources = [query.metadata["data_source"] for query in queries]
    return {
        "data_sources": list(set(data_sources)),
        "queries": queries,
        "dashboard": dashboard.get("dashboard"),
    }
