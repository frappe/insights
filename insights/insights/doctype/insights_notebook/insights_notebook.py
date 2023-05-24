# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsNotebook(Document):
    def on_trash(self):
        if self.name == "Uncategorized":
            frappe.throw("Cannot delete the default notebook")
