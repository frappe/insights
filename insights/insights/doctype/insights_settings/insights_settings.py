# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from insights import notify
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
        if hasattr(settings, "subscription_id"):
            self.subscription_id = settings.subscription_id
        self.save()

    @frappe.whitelist()
    @check_role("Insights User")
    def send_support_login_link(self):
        if frappe.session.user == "Administrator":
            frappe.throw("Administrator cannot access support portal")

        if not self.subscription_id:
            notify(
                type="error",
                title="Subscription ID not found",
                message="Please set your subscription ID in Insights Settings",
            )
            return

        portal_url = "https://frappeinsights.com"
        remote_method = "/api/method/send-remote-login-link"
        url = f"{portal_url}{remote_method}"

        subscription_id = self.get_password("subscription_id")
        email = frappe.session.user

        try:
            res = frappe.integrations.utils.make_post_request(
                url, data={"subscription_id": subscription_id, "email": email}
            )
            if res and res["message"]:
                notify(
                    title="Login link sent",
                    message=f"Login link sent to - {email}",
                )
            else:
                notify(
                    title="Error sending login link",
                    message="Error sending login link to your email",
                    type="error",
                )

        except Exception:
            frappe.log_error(title="Error sending login link for support portal")
            notify(
                title="Error sending login link",
                message="Error sending login link to your email",
                type="error",
            )
