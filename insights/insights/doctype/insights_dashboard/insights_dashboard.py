# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from json import dumps

import frappe
from frappe.model.document import Document


class InsightsDashboard(Document):
    @frappe.whitelist()
    def get_visualizations(self):
        visualizations = [row.visualization for row in self.visualizations]
        return frappe.get_all(
            "Query Visualization",
            filters={"name": ("not in", visualizations)},
            fields=["name", "title", "type"],
        )

    @frappe.whitelist()
    def add_visualization(self, visualization):
        self.append("visualizations", {"visualization": visualization})
        self.save()

    @frappe.whitelist()
    def update_visualization_layout(self, visualization, layout):
        row = self.get("visualizations", {"visualization": visualization})
        if not row:
            return
        row[0].layout = dumps(layout, indent=2)
        self.save()
