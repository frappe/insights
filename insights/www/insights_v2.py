# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt


import frappe

from insights.api.telemetry import track_active_site

no_cache = 1


def get_context(context):
    is_v2_user = frappe.db.count("Insights Query", cache=True) > 0
    if not is_v2_user:
        frappe.local.flags.redirect_location = "/insights"
        raise frappe.Redirect

    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()
    context.csrf_token = csrf_token
    context.site_name = frappe.local.site
    track_active_site()
