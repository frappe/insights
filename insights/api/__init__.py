# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.defaults import get_user_default, set_user_default
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
        {
            "parent": frappe.session.user,
            "role": ["in", ("Insights Admin", "System Manager")],
        },
    )
    is_user = frappe.db.exists(
        "Has Role",
        {
            "parent": frappe.session.user,
            "role": ["in", ("Insights User", "System Manager")],
        },
    )

    user = frappe.db.get_value(
        "User", frappe.session.user, ["first_name", "last_name"], as_dict=1
    )

    return {
        "email": frappe.session.user,
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "is_admin": is_admin or frappe.session.user == "Administrator",
        "is_user": is_user or frappe.session.user == "Administrator",
        # TODO: move to `get_session_info` since not user specific
        "country": frappe.db.get_single_value("System Settings", "country"),
        "locale": frappe.db.get_single_value("System Settings", "language"),
        "is_v2_user": frappe.db.count("Insights Query") > 0,
        "default_version": get_user_default(
            "insights_default_version", frappe.session.user
        ),
    }


@frappe.whitelist()
def update_default_version(version):
    if get_user_default("insights_has_visited_v3", frappe.session.user) != "1":
        set_user_default("insights_has_visited_v3", "1", frappe.session.user)

    if version not in ["v2", "v3", ""]:
        frappe.throw("Invalid Version")

    set_user_default("insights_default_version", version, frappe.session.user)


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
