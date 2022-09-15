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
        if not updated_layout.moved and not updated_layout.resized:
            return

        for item in updated_layout.moved:
            item = frappe._dict(item)
            self.move_visualization(item.from_index, item.to_index)
        for item in updated_layout.resized:
            item = frappe._dict(item)
            self.resize_visualization(item.name, item.width, item.height)
        self.save()

    def move_visualization(self, from_index, to_index):
        self.visualizations.insert(to_index, self.visualizations.pop(from_index))
        for row in self.visualizations:
            row.idx = self.visualizations.index(row) + 1

    def resize_visualization(self, name, width, height):
        for row in self.visualizations:
            if str(row.name) == str(name):
                row.layout = dumps({"width": width, "height": height}, indent=2)
                break
