# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.integrations.utils import make_get_request, make_post_request

from insights.api import get_app_version
from insights.api.subscription import get_subscription_key


def get_marketplace_url(throw=True):
    marketplace_url = frappe.conf.get("insights_marketplace_url")

    if not marketplace_url and throw:
        return frappe.throw(
            title="Marketplace URL not set",
            msg="Please set the marketplace URL in the site config.",
        )

    return marketplace_url


@frappe.whitelist()
def create_template(template):
    marketplace_url = get_marketplace_url()

    template = frappe._dict(template)
    dashboard = frappe.get_doc("Insights Dashboard", template.dashboard_name)
    dashboard_data = dashboard.export()

    try:
        make_post_request(
            marketplace_url + "/api/method/publish_template",
            data={
                "subscription_key": get_subscription_key(),
                "author": frappe.session.user,
                "author_name": frappe.db.get_value("User", frappe.session.user, "full_name"),
                "app_version": get_app_version(),
                "title": template.title,
                "description": template.description,
                "data": frappe.as_json(dashboard_data["data"]),
                "metadata": frappe.as_json(dashboard_data["metadata"]),
            },
        )

    except BaseException:
        frappe.log_error(title="Failed to publish template")
        frappe.throw(
            title="Failed to publish template",
            msg="Failed to publish template. Please try again.",
        )


@frappe.whitelist()
def get_my_templates():
    marketplace_url = get_marketplace_url(throw=False)
    if not marketplace_url:
        return []

    subscription_key = get_subscription_key()
    if not subscription_key:
        return []

    try:
        response = make_post_request(
            marketplace_url + "/api/method/get_user_templates",
            data={"subscription_key": subscription_key},
        )
        return response["message"]

    except BaseException:
        frappe.log_error(title="Failed to fetch templates")
        frappe.throw(
            title="Failed to fetch templates",
            msg="Failed to fetch templates. Please try again.",
        )


@frappe.whitelist()
def get_all_templates():
    marketplace_url = get_marketplace_url(throw=False)
    if not marketplace_url:
        return []

    try:
        response = make_get_request(marketplace_url + "/api/method/get_published_templates")
        return response["message"] or []

    except BaseException:
        frappe.log_error(title="Failed to fetch templates")
        frappe.throw(
            title="Failed to fetch templates",
            msg="Failed to fetch templates. Please try again.",
        )
