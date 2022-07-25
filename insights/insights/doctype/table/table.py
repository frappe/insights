# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Table(Document):
    def on_update(self):
        # clear cache
        frappe.cache().hdel(
            "insights",
            "get_tables_" + self.data_source,
        )
