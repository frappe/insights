# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from contextlib import suppress

import frappe
from frappe.utils.data import date_diff
from posthog import Posthog


@frappe.whitelist()
def get_credentials():
    return {
        "project_id": frappe.conf.get("posthog_project_id"),
        "host": frappe.conf.get("posthog_host"),
    }


@frappe.whitelist()
def track_active_site():
    is_frappe_cloud_site = frappe.conf.get("sk_insights")
    if (
        frappe.conf.developer_mode
        or not should_track_active_status()
        or not is_frappe_cloud_site
    ):
        return

    capture_event("insights_active_site")
    frappe.cache().set_value("last_active_at", frappe.utils.now_datetime())


def capture_event(event_name, properties=None):
    if not frappe.conf.get("posthog_project_id") or not frappe.conf.get("posthog_host"):
        return

    with suppress(Exception):
        ph = Posthog(
            frappe.conf.get("posthog_project_id"),
            host=frappe.conf.get("posthog_host"),
        )
        ph.capture(
            distinct_id=frappe.local.site, event=event_name, properties=properties
        )


def should_track_active_status():
    last_active_at = frappe.cache().get_value("last_active_at")
    if not last_active_at:
        return True

    last_active_at = frappe.utils.get_datetime(last_active_at)
    if date_diff(frappe.utils.now_datetime(), last_active_at) > 1:
        return True

    return False
