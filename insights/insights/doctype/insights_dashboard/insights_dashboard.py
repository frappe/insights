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
            "Insights Query Chart",
            filters={"name": ("not in", visualizations), "type": ["!=", "Pivot"]},
            fields=["name", "title", "type"],
        )

    @frappe.whitelist()
    def add_visualization(self, visualization):
        self.append("visualizations", {"visualization": visualization})
        self.save()

    @frappe.whitelist()
    def refresh_visualizations(self):
        for visualization in self.visualizations:
            try:
                frappe.get_doc("Insights Query", visualization.query).run()
            except BaseException:
                frappe.log_error(title="Error while executing query")

    @frappe.whitelist()
    def remove_visualization(self, visualization):
        for row in self.visualizations:
            if row.visualization == visualization:
                self.remove(row)
                self.save()
                break

    @frappe.whitelist()
    def update_layout(self, updated_layout):
        updated_layout = frappe._dict(updated_layout)
        if not updated_layout:
            return

        for row in self.visualizations:
            # row.name can be an interger which could get converted to a string
            if str(row.name) in updated_layout or row.name in updated_layout:
                new_layout = (
                    updated_layout.get(str(row.name))
                    or updated_layout.get(row.name)
                    or {}
                )
                row.layout = dumps(new_layout, indent=2)
        self.save()
