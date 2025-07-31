# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt


import re

import frappe
from frappe.defaults import get_user_default

from insights.api.telemetry import track_active_site

no_cache = 1

def get_context(context):
    setup_complete = check_setup_complete()
    if not setup_complete:
        frappe.local.flags.redirect_location = "/app/setup-wizard"
        raise frappe.Redirect
    is_v2_site = frappe.db.count("Insights Query", cache=True) > 0
    if not is_v2_site:
        continue_to_v3(context)
        return

    v2_routes_pattern = [
        r"\/insights\/query\/?",
        r"\/insights\/query\/build\/?",
        r"\/insights\/dashboard[^s]\/?",
        r"\/insights\/public\/dashboard\/?",
        r"\/insights\/public\/chart\/?",
    ]
    if any(re.match(route, frappe.request.path) for route in v2_routes_pattern):
        redirect_to_v2()
        return

    v3_routes = [
        "/insights/dashboards",
        "/insights/workbook",
        "/insights/shared/chart",
        "/insights/shared/dashboard",
    ]
    if any(route in frappe.request.path for route in v3_routes):
        continue_to_v3(context)
        return

    # go to v2 if user has not visited v3 yet
    has_visited_v3 = (
        get_user_default("insights_has_visited_v3", frappe.session.user) == "1"
    )
    if not has_visited_v3:
        redirect_to_v2()
        return

    is_v3_default = (
        get_user_default("insights_default_version", frappe.session.user) == "v3"
    )
    is_v2_default = (
        get_user_default("insights_default_version", frappe.session.user) == "v2"
    )

    if is_v3_default:
        continue_to_v3(context)
    elif is_v2_default:
        redirect_to_v2()
    else:
        continue_to_v3(context)


def continue_to_v3(context):
    try:
        from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
    except ImportError:

        def is_fc_site():
            return False

    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()
    context.boot = {
        "csrf_token": csrf_token,
        "site_name": frappe.local.site,
        "is_fc_site": is_fc_site(),
    }
    track_active_site(is_v3=True)


def redirect_to_v2():
    path = frappe.request.full_path
    path = path.replace("/insights", "/insights_v2")
    if not path.startswith("/insights_v2"):
        path = "/insights_v2"
    frappe.local.flags.redirect_location = path
    raise frappe.Redirect

def check_setup_complete():
    try:
        return frappe.is_setup_complete()
    except AttributeError:
        return frappe.db.get_single_value("System Settings", "setup_complete")