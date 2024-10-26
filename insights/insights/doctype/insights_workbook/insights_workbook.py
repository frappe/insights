# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe


from functools import cached_property

import frappe
import frappe.utils
from frappe.model.document import Document

from insights.api.workbooks import fetch_query_results


class InsightsWorkbook(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        charts: DF.JSON | None
        dashboards: DF.JSON | None
        name: DF.Int | None
        queries: DF.JSON | None
        title: DF.Data
    # end: auto-generated types

    def before_save(self):
        self.title = self.title or f"Workbook {frappe.utils.cint(self.name)}"
        # fix: json field value cannot be a list (see: base_document.py:get_valid_dict)
        self.queries = frappe.as_json(frappe.parse_json(self.queries))
        self.charts = frappe.as_json(frappe.parse_json(self.charts))
        self.dashboards = frappe.as_json(frappe.parse_json(self.dashboards))

    @cached_property
    def query_map(self):
        return {q["name"]: q for q in frappe.parse_json(self.queries)}

    def get_shared_chart_data(self, chart_name):
        chart = next(
            (c for c in frappe.parse_json(self.charts) if c["name"] == chart_name), None
        )
        if not chart:
            frappe.throw("Chart not found")

        if not chart.get("is_public"):
            frappe.throw("Chart is not shared")

        operations = chart.get("operations")
        if not operations:
            frappe.throw(f"Chart {chart_name} has no operations")

        chart_query = self.query_map.get(chart["query"])
        use_live_connection = chart_query.get("use_live_connection", True)
        operations = self.resolve_query_tables(operations)

        frappe.flags.ignore_insights_permissions = True
        results = fetch_query_results(operations, use_live_connection)
        frappe.flags.ignore_insights_permissions = False

        return {
            "chart": chart,
            "results": results,
        }

    def resolve_query_tables(self, operations):
        source_op = next((op for op in operations if op["type"] == "source"), None)
        if not source_op:
            return []

        if source_op["table"]["type"] == "query":
            query_name = source_op["table"]["query_name"]
            source_query = self.query_map.get(query_name)
            if not source_query:
                frappe.throw(f"Source query {query_name} not found")

            source_query_operations = self.resolve_query_tables(
                source_query["operations"]
            )
            current_operations_without_source = operations[1:]

            operations = source_query_operations + current_operations_without_source

        for op in operations:
            if op["type"] != "join" and op["type"] != "union":
                continue
            if op["table"]["type"] != "query":
                continue

            query_name = op["table"]["query_name"]
            query_table = self.query_map.get(query_name)
            if not query_table:
                frappe.throw(f"Query {query_name} not found")

            op["table"]["operations"] = self.resolve_query_tables(
                query_table["operations"]
            )

        return operations
