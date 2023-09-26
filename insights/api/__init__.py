# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.integrations.utils import make_post_request
from frappe.rate_limiter import rate_limit

from insights.decorators import check_role


@frappe.whitelist()
@check_role("Insights User")
def get_app_version():
    return frappe.get_attr("insights" + ".__version__")


@frappe.whitelist()
@check_role("Insights User")
def get_user_info():
    is_admin = frappe.db.exists(
        "Has Role",
        {"parent": frappe.session.user, "role": ["in", ("Insights Admin", "System Manager")]},
    )
    is_user = frappe.db.exists(
        "Has Role",
        {"parent": frappe.session.user, "role": ["in", ("Insights User", "System Manager")]},
    )

    user = frappe.db.get_value("User", frappe.session.user, ["first_name", "last_name"], as_dict=1)

    return {
        "user_id": frappe.session.user,
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "is_admin": is_admin or frappe.session.user == "Administrator",
        "is_user": is_user or frappe.session.user == "Administrator",
        # TODO: move to `get_session_info` since not user specific
        "country": frappe.db.get_single_value("System Settings", "country"),
        "locale": frappe.db.get_single_value("System Settings", "language"),
    }


@frappe.whitelist()
@rate_limit(limit=10, seconds=60 * 60)
def contact_team(message_type, message_content, is_critical=False):
    if not message_type or not message_content:
        frappe.throw("Message Type and Content are required")

    message_title = {
        "Feedback": "Feedback from Insights User",
        "Bug": "Bug Report from Insights User",
        "Question": "Question from Insights User",
    }.get(message_type)

    if not message_title:
        frappe.throw("Invalid Message Type")

    try:
        make_post_request(
            "https://frappeinsights.com/api/method/contact-team",
            data={
                "message_title": message_title,
                "message_content": message_content,
            },
        )
    except Exception as e:
        frappe.log_error(e)
        frappe.throw("Something went wrong. Please try again later.")
