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
        is_public: DF.Check
        old_name: DF.Data | None
        query: DF.Link | None
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


def import_chart(chart, workbook):
    chart = frappe.parse_json(chart)
    chart = deep_convert_dict_to_dict(chart)

    new_chart = frappe.new_doc("Insights Chart v3")
    new_chart.update(chart.doc)
    new_chart.workbook = workbook
    new_chart.insert()

    if str(workbook) == str(chart.doc.workbook) or not chart.dependencies.queries:
        return new_chart.name

    for _, exported_query in chart.dependencies.queries.items():
        name = import_query(exported_query, workbook=new_chart.workbook)
        new_chart.db_set("query", name, update_modified=False)

    return new_chart.name
