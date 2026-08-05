# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe


def after_migrate():
    try:
        create_admin_team()
    except Exception:
        frappe.log_error(title="Error creating Admin Team")

    try:
        from insights.api.templates import sync_workbook_template_updates

        sync_workbook_template_updates()
    except Exception:
        frappe.log_error(title="Error syncing workbook template updates")

    # every app's shipped analytics, reconciled into documents. sync_bundles
    # isolates each app itself; this catch is for discovery blowing up before
    # any app is reached.
    try:
        from insights.bundles import sync_bundles

        sync_bundles()
    except Exception:
        frappe.log_error(title="Error syncing Insights bundles")


def create_admin_team():
    if not frappe.db.exists("Insights Team", "Admin"):
        frappe.get_doc(
            {
                "doctype": "Insights Team",
                "team_name": "Admin",
                "team_members": [{"user": "Administrator"}],
            }
        ).insert(ignore_permissions=True)
