# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class InsightsWorkbook(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        data_backup: DF.JSON | None
        name: DF.Int | None
        title: DF.Data
    # end: auto-generated types

    def before_save(self):
        self.title = self.title or f"Workbook {frappe.utils.cint(self.name)}"

    def on_trash(self):
        for q in frappe.get_all("Insights Query v3", {"workbook": self.name}):
            frappe.delete_doc(
                "Insights Query v3", q.name, force=True, ignore_permissions=True
            )
        for c in frappe.get_all("Insights Chart v3", {"workbook": self.name}):
            frappe.delete_doc(
                "Insights Chart v3", c.name, force=True, ignore_permissions=True
            )
        for d in frappe.get_all("Insights Dashboard v3", {"workbook": self.name}):
            frappe.delete_doc(
                "Insights Dashboard v3", d.name, force=True, ignore_permissions=True
            )

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)
        chart_queries = frappe.get_all(
            "Insights Chart v3",
            filters={"workbook": self.name},
            pluck="data_query",
        )
        d.queries = frappe.get_all(
            "Insights Query v3",
            filters={
                "workbook": self.name,
                "name": ["not in", chart_queries],
            },
            fields=[
                "name",
                "title",
                "is_native_query",
                "is_builder_query",
                "is_script_query",
            ],
            order_by="creation asc",
        )
        d.charts = frappe.get_all(
            "Insights Chart v3",
            filters={"workbook": self.name},
            fields=[
                "name",
                "title",
                "chart_type",
                "query",
            ],
            order_by="creation asc",
        )
        d.dashboards = frappe.get_all(
            "Insights Dashboard v3",
            filters={"workbook": self.name},
            fields=["name", "title"],
            order_by="creation asc",
        )
        d.queries = frappe.as_json(d.queries)
        d.charts = frappe.as_json(d.charts)
        d.dashboards = frappe.as_json(d.dashboards)
        d.read_only = not self.has_permission("write")
        return d

    @frappe.whitelist()
    def track_view(self):
        view_log = frappe.qb.DocType("View Log")
        last_viewed_recently = frappe.db.get_value(
            view_log,
            filters=(
                (view_log.creation > (Now() - Interval(minutes=5)))
                & (view_log.reference_doctype == self.doctype)
                & (view_log.reference_name == self.name)
                & (view_log.viewed_by == frappe.session.user)
            ),
            pluck="name",
        )
        if not last_viewed_recently:
            self.add_viewed(force=True)
