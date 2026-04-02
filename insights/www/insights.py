# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt


import frappe

from insights.api.telemetry import track_active_site

no_cache = 1


def get_context(context):
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
        "socketio_port": frappe.conf.get("socketio_port"),
    }
    track_active_site(is_v3=True)
