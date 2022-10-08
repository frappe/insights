# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from json import dumps

import frappe
from frappe.model.document import Document


class InsightsDashboard(Document):
    def validate(self):
        self.validate_duplicate_charts()

    def validate_duplicate_charts(self):
        charts = [d.query_chart for d in self.items if d.query_chart]
        if len(charts) != len(set(charts)):
            duplicates = [item for item in charts if charts.count(item) > 1]
            frappe.throw("Duplicate charts found: {0}".format(", ".join(duplicates)))

    @frappe.whitelist()
    def get_charts(self):
        charts = [row.query_chart for row in self.items if row.query_chart]
        return frappe.get_all(
            "Insights Query Chart",
            filters={"name": ("not in", charts), "type": ["!=", "Pivot"]},
            fields=["name", "title", "type"],
        )

    @frappe.whitelist()
    def add_chart(self, chart, layout=None):
        if not layout:
            layout = {"w": 8, "h": 8}
        self.append(
            "items",
            {
                "query_chart": chart,
                "layout": dumps(layout, indent=2),
            },
        )
        self.save()

    @frappe.whitelist()
    def refresh_items(self):
        for item in self.items:
            try:
                frappe.get_doc("Insights Query", item.query).run()
            except BaseException:
                frappe.log_error(title="Error while executing query")

    @frappe.whitelist()
    def remove_item(self, item):
        for row in self.items:
            if row.name == item:
                self.remove(row)
                self.save()
                break

    @frappe.whitelist()
    def update_layout(self, updated_layout):
        updated_layout = frappe._dict(updated_layout)
        if not updated_layout:
            return

        for row in self.items:
            # row.name can be an interger which could get converted to a string
            if str(row.name) in updated_layout or row.name in updated_layout:
                new_layout = (
                    updated_layout.get(str(row.name))
                    or updated_layout.get(row.name)
                    or {}
                )
                row.layout = dumps(new_layout, indent=2)
        self.save()
