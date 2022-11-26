# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsSettings(Document):
    @frappe.whitelist()
    def update_settings(self, settings):
        settings = frappe.parse_json(settings)
        self.auto_execute_query = settings.auto_execute_query or self.auto_execute_query
        self.auto_refresh_dashboard_in_minutes = (
            settings.auto_refresh_dashboard_in_minutes
            or self.auto_refresh_dashboard_in_minutes
        )
        self.save()
