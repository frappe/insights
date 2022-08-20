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
    def refresh_visualizations(self):
        for visualization in self.visualizations:
            frappe.get_doc("Query", visualization.query).run()

    @frappe.whitelist()
    def remove_visualization(self, visualization):
        for row in self.visualizations:
            if row.visualization == visualization:
                self.remove(row)
                self.save()
                break

    @frappe.whitelist()
    def update_layout(self, visualizations):
        for visualization, layout in visualizations.items():
            row = self.get("visualizations", {"visualization": visualization})
            if not row:
                continue
            row[0].layout = dumps(layout, indent=2)
        self.save()
