# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from json import dumps

import frappe
from frappe import _dict
from frappe.model.document import Document


class InsightsQueryChart(Document):
    def on_trash(self):
        frappe.db.delete("Insights Dashboard Item", {"visualization": self.name})

    @frappe.whitelist()
    def update_doc(self, doc):
        doc = _dict(doc)
        self.title = doc.title
        self.type = doc.type
        self.data = dumps(doc.data, indent=2)
        self.save()

    @frappe.whitelist()
    def add_to_dashboard(self, dashboard, layout=None):
        if not dashboard:
            frappe.throw("Dashboard is required")
        dashboard_doc = frappe.get_doc("Insights Dashboard", dashboard)
        dashboard_doc.add_visualization(self.name, layout)  # saves the dashboard
