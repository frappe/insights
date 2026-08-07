# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe


def after_migrate():
    try:
        create_admin_team()
    except Exception:
        frappe.log_error(title="Error creating Admin Team")

    # every app's shipped analytics, reconciled into documents.
    # sync_standard_content isolates each app itself; this catch is for discovery
    # blowing up before any app is reached.
    try:
        from insights.standard_content import sync_standard_content

        sync_standard_content()
    except Exception:
        frappe.log_error(title="Error syncing Insights standard content")


def create_admin_team():
    if not frappe.db.exists("Insights Team", "Admin"):
        frappe.get_doc(
            {
                "doctype": "Insights Team",
                "team_name": "Admin",
                "team_members": [{"user": "Administrator"}],
            }
        ).insert(ignore_permissions=True)
