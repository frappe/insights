# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from json import dumps

import frappe
from frappe import _dict
from frappe.model.document import Document


class InsightsQueryChart(Document):
    @frappe.whitelist()
    def update_doc(self, doc):
        doc = _dict(doc)
        self.title = doc.title
        self.type = doc.type
        self.config = dumps(doc.config, indent=2)
        self.save()

    @frappe.whitelist()
    def add_to_dashboard(self, dashboard):
        dashboard_doc = frappe.get_doc("Insights Dashboard", dashboard)
        dashboard_doc.add_item(
            {
                "item_type": "Chart",
                "chart": self.name,
            }
        )
