# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import random
from json import dumps

import frappe
from frappe.model.document import Document

from insights import notify
from insights.api.permissions import is_private
from insights.api.telemetry import track
from insights.cache_utils import get_or_set_cache, make_digest
from insights.decorators import debounce
from insights.insights.doctype.insights_query.utils import import_query

from .utils import (
    convert_into_simple_filter,
    convert_to_expression,
    guess_layout_for_chart,
)

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
        notify(**{"type": "success", "title": "Cache Cleared"})

    @frappe.whitelist()
    def fetch_chart_data(self, item_id, query_name=None, filters=None):
        row = next((row for row in self.items if row.item_id == item_id), None)
        if not row and not query_name:
            return frappe.throw("Item not found")

        query_name = query_name or frappe.parse_json(row.options).query
        if not query_name:
            return frappe.throw("Query not found")

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

        return InsightsDashboard.run_query(
            self.cache_namespace, query_name, additional_filters=filter_conditions
        )

    @staticmethod
    @debounce(2)
    def run_query(cache_namespace, query_name, additional_filters=None):
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
                        existing_simple_filter = convert_into_simple_filter(exisiting_filter)
                        if not existing_simple_filter:
                            continue
                        if existing_simple_filter["column"] == new_simple_filter["column"]:
                            new_filters.conditions[index] = new_filter
                            found = True
                            break
                if not found:
                    new_filters.conditions.append(new_filter)

            query.filters = dumps(new_filters)
            return query.fetch_results()

        last_modified = frappe.db.get_value("Insights Query", query_name, "modified")
        key = make_digest(query_name, last_modified, additional_filters)
        key = f"{cache_namespace}:{key}"

        query_result_expiry = frappe.db.get_single_value(
            "Insights Settings", "query_result_expiry"
        )
        query_result_expiry_in_seconds = query_result_expiry * 60
        return get_or_set_cache(key, get_result, expiry=query_result_expiry_in_seconds)

    def export(self):
        return export_dashboard(self)

    @frappe.whitelist()
    def export_dashboard(self):
        exported_dashboard = self.export()
        filename = frappe.scrub(self.title.lower())
        file = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"{filename}.json",
                "content": exported_dashboard,
            }
        )
        file.save(ignore_permissions=True)
        return {
            "file_name": f"{filename}.json",
            "file_url": file.file_url,
        }


@frappe.whitelist()
def get_queries_column(query_names):
    # TODO: handle permissions
    table_by_datasource = {}
    for query in list(set(query_names)):
        # TODO: to further optimize, store the used tables in the query on save
        doc = frappe.get_cached_doc("Insights Query", query)
        for table in doc.get_selected_tables():
            if doc.data_source not in table_by_datasource:
                table_by_datasource[doc.data_source] = {}
            table_by_datasource[doc.data_source][table.table] = table

    columns = []
    for data_source in table_by_datasource.values():
        for table in data_source.values():
            doc = frappe.get_cached_doc(
                "Insights Table", {"table": table.table, "data_source": doc.data_source}
            )
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


def get_dashboard_public_key(name):
    existing_key = frappe.db.get_value("Insights Dashboard", name, "public_key", cache=True)
    if existing_key:
        return existing_key

    public_key = frappe.generate_hash()
    frappe.db.set_value("Insights Dashboard", name, "public_key", public_key)
    return public_key


def export_dashboard(doc):
    queries = {}
    for items in doc.items:
        options = frappe.parse_json(items.options)
        if "query" in options and options.query not in queries:  # query
            query_doc = frappe.get_doc("Insights Query", options.query)
            queries[options.query] = query_doc.export()

        # don't need to export queries from filters
        # because any column used in filter will be from the charts' query

    dashboard_dict = doc.as_dict()
    data_sources = [query.metadata["data_source"] for query in queries.values()]
    exported_dashboard = frappe._dict(
        data_sources=list(set(data_sources)),
        queries=queries,
        dashboard={
            "title": dashboard_dict["title"],
            "items": dashboard_dict["items"],
        },
    )
    return frappe.as_json(exported_dashboard)


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


@frappe.whitelist()
def import_dashboard(filename, title=None, data_source_map=None):
    file = frappe.get_doc("File", filename)
    dashboard = file.get_content()

    dashboard = frappe.parse_json(dashboard)
    queries = dashboard.get("queries")

    imported_queries = {}
    for name, query in queries.items():
        if name in imported_queries:
            continue
        query = frappe.parse_json(query)
        query_data_source = query.metadata["data_source"]
        data_source = data_source_map.get(query_data_source)
        query_name = import_query(data_source, query)
        imported_queries[name] = query_name

    # update old to new query names in dashboard
    dashboard_dict = dashboard.get("dashboard")
    for item in dashboard_dict["items"]:
        options = frappe.parse_json(item["options"])
        if "query" in options:
            options["query"] = imported_queries[options["query"]]
        item["options"] = frappe.as_json(options)

    dashboard_doc = frappe.new_doc("Insights Dashboard")
    dashboard_doc.title = title or dashboard_dict["title"]
    dashboard_doc.set("items", dashboard_dict["items"])
    dashboard_doc.insert(ignore_permissions=True)

    return dashboard_doc.name
