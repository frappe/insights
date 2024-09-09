# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt


import frappe
from frappe.defaults import get_user_default

from insights.api.telemetry import track_active_site

no_cache = 1


def get_context(context):
    is_v2_user = frappe.db.count("Insights Query", cache=True) > 0
    # if not v2 user continue to v3
    if not is_v2_user:
        continue_to_v3(context)
        return

    # go to v2 if user has not visited v3 yet
    has_visited_v3 = (
        get_user_default("insights_has_visited_v3", frappe.session.user) == "1"
    )
    if not has_visited_v3:
        redirect_to_v2()
        return

    v2_routes = [
        "/insights/query",
        "/insights/query/build",
        "/insights/dashboard",
        "/insights/public/dashboard",
        "/insights/public/chart",
    ]
    if any(route in frappe.request.path for route in v2_routes):
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
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()
    context.csrf_token = csrf_token
    context.site_name = frappe.local.site
    track_active_site(is_v3=True)


def redirect_to_v2():
    path = frappe.request.full_path
    frappe.local.flags.redirect_location = path.replace("/insights", "/insights_v2")
    raise frappe.Redirect
