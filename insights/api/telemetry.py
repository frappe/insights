# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from contextlib import suppress

import frappe
from frappe.utils.data import date_diff
from frappe.utils.telemetry import POSTHOG_HOST_FIELD, POSTHOG_PROJECT_FIELD
from posthog import Posthog

from insights.decorators import insights_whitelist


@frappe.whitelist()
def is_enabled():
    return bool(
        frappe.get_system_settings("enable_telemetry")
        and frappe.conf.get("posthog_host")
        and frappe.conf.get("posthog_project_id")
    )


@insights_whitelist()
def get_posthog_settings():
    can_record_session = False
    if start_time := frappe.db.get_default("session_recording_start"):
        time_difference = (
            frappe.utils.now_datetime() - frappe.utils.get_datetime(start_time)
        ).total_seconds()
        if time_difference < 86400:  # 1 day
            can_record_session = True

    return {
        "posthog_project_id": frappe.conf.get(POSTHOG_PROJECT_FIELD),
        "posthog_host": frappe.conf.get(POSTHOG_HOST_FIELD),
        "enable_telemetry": frappe.get_system_settings("enable_telemetry"),
        "telemetry_site_age": frappe.utils.telemetry.site_age(),
        "record_session": can_record_session,
        "posthog_identifier": frappe.local.site,
    }


@frappe.whitelist()
def get_credentials():
    return {
        "posthog_project_id": frappe.conf.get(POSTHOG_PROJECT_FIELD),
        "posthog_host": frappe.conf.get(POSTHOG_HOST_FIELD),
    }


@frappe.whitelist(allow_guest=True)
def track_active_site(is_v3=False):
    if (
        frappe.conf.developer_mode
        or not should_track_active_status()
        or not frappe.conf.get(POSTHOG_PROJECT_FIELD)
    ):
        return

    capture_event("insights_v3_active_site" if is_v3 else "insights_active_site")
    frappe.cache().set_value("last_active_at", frappe.utils.now_datetime())


def capture_event(event_name, properties=None):
    project_id = frappe.conf.get(POSTHOG_PROJECT_FIELD)
    host = frappe.conf.get(POSTHOG_HOST_FIELD)
    if not project_id or not host:
        return

    with suppress(Exception):
        ph = Posthog(project_id, host=host)
        ph.capture(
            distinct_id=frappe.local.site,
            event=event_name,
            properties=properties,
        )


def should_track_active_status():
    last_active_at = frappe.cache().get_value("last_active_at")
    if not last_active_at:
        return True

    last_active_at = frappe.utils.get_datetime(last_active_at)
    if date_diff(frappe.utils.now_datetime(), last_active_at) > 1:
        return True

    return False
