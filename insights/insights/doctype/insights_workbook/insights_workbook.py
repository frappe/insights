# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from contextlib import contextmanager
from functools import cached_property

import frappe
import frappe.utils
import requests
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
        self.enqueue_update_dashboard_previews()

    @cached_property
    def query_map(self):
        return {q["name"]: q for q in frappe.parse_json(self.queries)}

    def get_shared_chart_data(self, chart_name):
        chart = next(
            (c for c in frappe.parse_json(self.charts) if c["name"] == chart_name), None
        )
        if not chart:
            frappe.throw("Chart not found")

        if not self.can_access_shared_chart(chart):
            frappe.throw("Chart cannot be accessed")

        operations = chart.get("operations")
        if not operations:
            return {
                "chart": chart,
                "results": [],
            }

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

    def can_access_shared_chart(self, chart):
        if frappe.has_permission(doc=self, ptype="write"):
            return True

        if chart.get("is_public"):
            return True

        preview_key = frappe.request.headers.get("X-Insights-Preview-Key")
        if preview_key and frappe.cache.get_value(
            f"insights_preview_key:{preview_key}"
        ):
            return True

        return False

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

    def enqueue_update_dashboard_previews(self):
        if (
            self.is_new()
            or not frappe.parse_json(self.dashboards)
            or not self.get_doc_before_save()
        ):
            return

        prev_workbook = self.get_doc_before_save()
        frappe.enqueue_doc(
            doctype=self.doctype,
            name=self.name,
            method="update_dashboard_previews",
            new_workbook=self.as_dict(),
            prev_workbook=prev_workbook.as_dict(),
            enqueue_after_commit=True,
        )

    def update_dashboard_previews(self, new_workbook, prev_workbook):
        new_dashboards = frappe.parse_json(new_workbook.dashboards)

        for dashboard in new_dashboards:
            if not len(dashboard["items"]):
                continue

            if not has_dashboard_changed(
                dashboard["name"],
                new_workbook,
                prev_workbook,
            ):
                continue

            with generate_preview_key() as key:
                preview = get_page_preview(
                    frappe.utils.get_url(
                        f"/insights/shared/dashboard/{dashboard['name']}"
                    ),
                    headers={
                        "X-Insights-Preview-Key": key,
                    },
                )
                create_preview_file(preview, dashboard["name"], self.name)


def has_dashboard_changed(dashboard_name, new_workbook, prev_workbook):
    new_dashboards = frappe.parse_json(new_workbook.dashboards)
    old_dashboards = frappe.parse_json(prev_workbook.dashboards)
    new_charts = frappe.parse_json(new_workbook.charts)
    old_charts = frappe.parse_json(prev_workbook.charts)

    new_dashboard = next(
        (d for d in new_dashboards if d["name"] == dashboard_name), None
    )
    old_dashboard = next(
        (d for d in old_dashboards if d["name"] == dashboard_name), None
    )
    if not new_dashboard or not old_dashboard:
        return True

    new_items = new_dashboard["items"]
    old_items = old_dashboard["items"]
    if new_items != old_items:
        return True

    new_charts = [chart["name"] for chart in new_charts if chart["name"] in new_items]
    old_charts = [chart["name"] for chart in old_charts if chart["name"] in old_items]
    if new_charts != old_charts:
        return True

    new_chart_operations = [
        chart["operations"] for chart in new_charts if chart["name"] in new_items
    ]
    old_chart_operations = [
        chart["operations"] for chart in old_charts if chart["name"] in old_items
    ]
    if new_chart_operations != old_chart_operations:
        return True

    return False


def get_page_preview(url: str, headers: dict | None = None) -> bytes:
    PREVIEW_GENERATOR_URL = (
        frappe.conf.preview_generator_url
        or "https://preview.frappe.cloud/api/method/preview_generator.api.generate_preview_from_url"
    )

    response = requests.post(
        PREVIEW_GENERATOR_URL,
        json={
            "url": url,
            "headers": headers or {},
            "wait_for": 1000,
        },
    )
    if response.status_code == 200:
        return response.content
    else:
        exception = response.json().get("exc")
        raise Exception(frappe.parse_json(exception)[0])


def create_preview_file(content: bytes, dashboard_name: str, workbook_name: str):
    file_name = f"{dashboard_name}-preview.jpeg"
    if filename := frappe.db.exists(
        "File",
        {
            "file_name": file_name,
            "attached_to_doctype": "Insights Workbook",
            "attached_to_name": workbook_name,
        },
    ):
        file = frappe.get_doc("File", filename)
        file.content = content
        file.save_file(overwrite=True)
        file.save()
    else:
        file = frappe.new_doc("File")
        file.attached_to_doctype = "Insights Workbook"
        file.attached_to_name = workbook_name
        file.folder = "Home/Attachments"
        file.file_name = file_name
        file.is_private = 1
        # insert file while ensuring file name is same as the one we want
        # first insert without content to reserve the file name (ignoring validate_file_on_disk)
        # then overwrite the file with the content
        file.flags.ignore_validate = True
        file.insert()
        file.flags.ignore_validate = False
        file.content = content
        file.save_file(overwrite=True)
        file.save()


@contextmanager
def generate_preview_key():
    try:
        key = frappe.generate_hash()
        frappe.cache.set_value(f"insights_preview_key:{key}", True)
        yield key
    finally:
        frappe.cache.delete_value(f"insights_preview_key:{key}")
