# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from json import dumps

import frappe
from frappe import _dict
from frappe.model.document import Document


class QueryVisualization(Document):
    def on_trash(self):
        frappe.db.delete("Insights Dashboard Item", {"visualization": self.name})

    @frappe.whitelist()
    def update_doc(self, doc):
        doc = _dict(doc)
        self.title = doc.title
        self.type = doc.type
        self.data = dumps(doc.data, indent=2)
        self.save()
