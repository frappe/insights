# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from insights import notify
from insights.api.subscription import get_subscription_key
from insights.decorators import check_role


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
        except BaseException:
            return None

    @frappe.whitelist()
    @check_role("Insights User")
    def send_support_login_link(self):
        if frappe.session.user == "Administrator":
            frappe.throw("Administrator cannot access support portal")

        subscription_key = get_subscription_key()
        if not subscription_key:
            notify(type="error", title="Subscription Key not found")
            return

        portal_url = "https://frappeinsights.com"
        remote_method = "/api/method/send-remote-login-link"
        url = f"{portal_url}{remote_method}"
        email = frappe.session.user

        try:
            frappe.integrations.utils.make_post_request(
                url, data={"subscription_key": subscription_key, "email": email}
            )
            notify(
                title="Login link sent",
                message=f"Login link sent to - {email}",
            )
        except Exception:
            frappe.log_error(title="Error sending login link to your email")
            notify(
                title="Something went wrong",
                message="Error sending login link to your email",
                type="error",
            )
