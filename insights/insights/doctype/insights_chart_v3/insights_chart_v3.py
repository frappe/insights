# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from insights.insights.doctype.insights_chart_v3.chart_query import config_errors, derive_operations
from insights.insights.doctype.insights_data_source_v3.data_authority import data_authority_of
from insights.insights.doctype.insights_query_v3.insights_query_v3 import import_query
from insights.utils import deep_convert_dict_to_dict

QUERY = "Insights Query v3"


class InsightsChartv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        chart_type: DF.Data | None
        config: DF.JSON | None
        data_authority: DF.Literal["Viewer", "Author"]
        data_query: DF.Link | None
        folder: DF.Data | None
        is_public: DF.Check
        old_name: DF.Data | None
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
    def get_data(
        self,
        force: bool = False,
        page: int = 1,
        page_size: int = 100,
        adhoc_filters: dict | None = None,
    ):
        """Fetch this chart's rows under the authority declared on this document.

        A request may name a chart but must not describe one: `run_doc_method` builds
        `self` out of the request payload, so the stored chart is re-read here and it
        alone decides the authority and the query that runs under it.
        """
        chart = frappe.get_doc(self.doctype, self.name)
        query = chart.get_query()
        with data_authority_of(chart):
            return query.execute(
                force=force,
                page=page,
                page_size=page_size,
                adhoc_filters=adhoc_filters,
            )

    def get_query(self):
        """A query document for this chart's operations, made to run and thrown away.

        Nothing about it is worth keeping: the operations follow from the config, so
        the config is the only copy. It is never inserted, and it names the source
        query as its execution reference so a chart run still counts as usage of the
        tables it read.
        """
        query = frappe.new_doc(QUERY)
        query.name = self.name
        query.title = self.title
        query.workbook = self.workbook
        query.operations = frappe.as_json(self.get_operations())
        query.use_live_connection = frappe.db.get_value(QUERY, self.query, "use_live_connection")
        query.flags.execution_reference = self.query
        return query

    def get_operations(self):
        """The operations that produce the chart's rows.

        The source query, the chart's own filters, its summarize or pivot, and its
        sort — derived here from the config every time the chart runs. This used to
        be read off a second query document the browser filled in, and a chart no
        browser had visited fell back to drawing its source query: a whole shipped
        bundle rendered raw tables, every number wrong and nothing said so. A config
        that cannot be drawn is an error, not a row set.
        """
        config = frappe.parse_json(self.config or "{}")
        errors = config_errors(self.chart_type, self.query, config)
        if errors:
            frappe.throw(
                _("Chart {0} is not configured: {1}. Open it in Insights to configure it.").format(
                    frappe.bold(self.title or self.name), ", ".join(errors)
                ),
                title=_("Chart is not configured"),
            )

        return derive_operations(self.chart_type, self.query, config)

    @frappe.whitelist()
    def export(self):
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
    chart = frappe.parse_json(chart)
    chart = deep_convert_dict_to_dict(chart)

    new_chart = frappe.new_doc("Insights Chart v3")
    new_chart.update(chart.doc)
    new_chart.workbook = workbook

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

    if str(workbook) == str(chart.doc.workbook) or not chart.dependencies.queries:
        return new_chart.name

    for exported_query in chart.dependencies.queries.values():
        name = import_query(exported_query, workbook=new_chart.workbook)
        new_chart.db_set("query", name, update_modified=False)

    return new_chart.name
