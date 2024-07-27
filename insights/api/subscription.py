# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.integrations.utils import make_post_request


def get_subscription_key():
    try:
        return frappe.conf.sk_insights
    except Exception:
        return None


def get_subscription_info():
    secret_key = get_subscription_key()
    if not secret_key:
        return {}
    try:
        res = make_post_request(
            "https://frappecloud.com/api/method/press.api.developer.marketplace.get_subscription_info",
            data={"secret_key": secret_key},
        )
        return res["message"]
    except Exception:
        return None


@frappe.whitelist()
def trial_expired():
    subscription_info = get_subscription_info()
    if not subscription_info:
        return None
    plan = subscription_info.get("plan", "")
    expiry = frappe.utils.get_datetime(subscription_info.get("end_date", "3000-01-01"))
    return "trial" in plan.lower() and expiry < frappe.utils.now_datetime()
