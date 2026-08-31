# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from insights.insights.doctype.insights_query_v3.insights_query_v3 import import_query
from insights.utils import deep_convert_dict_to_dict


class InsightsChartv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        chart_type: DF.Data | None
        config: DF.JSON | None
        data_query: DF.Link | None
        folder: DF.Data | None
        is_public: DF.Check
        old_name: DF.Data | None
        permission_user: DF.Link | None
        query: DF.Link | None
        sort_order: DF.Int
        title: DF.Data | None
        workbook: DF.Link
    # end: auto-generated types

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.config, dict):
            self.config = frappe.as_json(self.config)
        return super().get_valid_dict(*args, **kwargs)

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)
        d.read_only = not self.has_permission("write")
        return d

    def validate(self):
        from insights.permissions import check_chart_query_access

        check_chart_query_access(self)

    @frappe.whitelist()
    def update_access(self, is_public: bool):
        """Publish this chart, or withdraw it.

        Publishing is a grant of the publisher's own read access to everyone
        with the link, so it is the `share` permission and not `write`. The
        publisher is recorded here because the public execution has no caller of
        its own to filter rows by. `is_public` and `permission_user` are both
        permlevel 1, so this method is the only way in.

        The `query` link needs no check here. This writes neither link nor
        content, and a caller who reached this method can read the chart, which
        `_build_query_permission_query` already turns into read on its query.
        """
        if not frappe.has_permission("Insights Chart v3", ptype="share", doc=self.name):
            frappe.throw(frappe._("You do not have permission to share this chart"), frappe.PermissionError)

        is_public = bool(frappe.parse_json(is_public))
        self.db_set(
            {
                "is_public": int(is_public),
                "permission_user": frappe.session.user if is_public else None,
            }
        )

    def before_save(self):
        self.set_data_query()

    def on_trash(self):
        frappe.delete_doc("Insights Query v3", self.data_query, force=True, ignore_permissions=True)

        # Clean up empty folders
        if self.folder:
            self.cleanup_empty_folder(self.folder)

    def cleanup_empty_folder(self, folder_name):
        """Delete folder if it has no queries or charts"""
        if not frappe.db.exists("Insights Folder", folder_name):
            return

        folder = frappe.get_doc("Insights Folder", folder_name)
        folder_type = folder.type

        if folder_type == "query":
            has_items = frappe.db.exists("Insights Query v3", {"folder": folder_name})
        else:
            has_items = frappe.db.exists("Insights Chart v3", {"folder": folder_name})

        if not has_items:
            frappe.delete_doc("Insights Folder", folder_name, force=True, ignore_permissions=True)

    def set_data_query(self):
        if self.data_query:
            return
        doc = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook,
            }
        )
        doc.db_insert()
        self.data_query = doc.name

    @frappe.whitelist()
    def export(self):
        from insights.permissions import check_referenced_query_access

        chart = {
            "version": "1.0",
            "timestamp": frappe.utils.now(),
            "type": "Chart",
            "name": self.name,
            "doc": {
                "name": self.name,
                "title": self.title,
                "workbook": self.workbook,
                "query": self.query,
                "chart_type": self.chart_type,
                "config": frappe.parse_json(self.config),
            },
            "dependencies": {
                "queries": {},
            },
        }

        check_referenced_query_access(self.query)
        exported_query = frappe.get_doc("Insights Query v3", self.query).export()
        chart["dependencies"]["queries"][self.query] = exported_query

        return chart

    @frappe.whitelist()
    def duplicate(self):
        new_chart = frappe.copy_doc(self)
        new_chart.title = f"{self.title} (Copy)"
        new_chart.data_query = None
        new_chart.insert()
        return new_chart.name


def import_chart(chart, workbook):
    """Copy an exported chart into `workbook`, with the query it is built on.

    The query goes in first, so the chart is inserted already pointing at the
    copy. `validate` reads the link, and a link to the exporting site's query is
    a state it would read as the real one.
    """
    from insights.insights.doctype.insights_query_v3.insights_query_v3 import already_in_workbook

    chart = frappe.parse_json(chart)
    chart = deep_convert_dict_to_dict(chart)

    new_chart = frappe.new_doc("Insights Chart v3")
    new_chart.update(chart.doc)
    new_chart.workbook = workbook

    exported = (chart.get("dependencies") or {}).get("queries") or {}
    if chart.doc.query in exported and not already_in_workbook(chart.doc.query, workbook):
        new_chart.query = import_query(exported[chart.doc.query], workbook)

    if not hasattr(new_chart, "sort_order") or new_chart.sort_order is None:
        max_sort_order = (
            frappe.db.get_value(
                "Insights Chart v3",
                filters={"workbook": workbook},
                fieldname="max(sort_order)",
            )
            or -1
        )
        new_chart.sort_order = max_sort_order + 1
    new_chart.insert()

    return new_chart.name
