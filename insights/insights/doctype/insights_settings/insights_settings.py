# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsSettings(Document):
    @frappe.whitelist()
    def update_settings(self, settings):
        settings = frappe.parse_json(settings)
        if hasattr(settings, "auto_execute_query"):
            self.auto_execute_query = settings.auto_execute_query
        if hasattr(settings, "query_result_expiry"):
            self.query_result_expiry = settings.query_result_expiry
        if hasattr(settings, "query_result_limit"):
            self.query_result_limit = settings.query_result_limit
        if hasattr(settings, "allow_subquery"):
            self.allow_subquery = settings.allow_subquery
        if hasattr(settings, "telegram_api_token"):
            self.telegram_api_token = settings.telegram_api_token
        self.save()

    @property
    def is_subscribed(self):
        try:
            return 1 if frappe.conf.sk_insights else 0
        except Exception:
            return None
