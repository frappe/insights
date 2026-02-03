# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe


def after_migrate():
    try:
        create_admin_team()
    except Exception:
        frappe.log_error(title="Error creating Admin Team")


def create_admin_team():
    if not frappe.db.exists("Insights Team", "Admin"):
        frappe.get_doc(
            {
                "doctype": "Insights Team",
                "team_name": "Admin",
                "team_members": [{"user": "Administrator"}],
            }
        ).insert(ignore_permissions=True)

<<<<<<< HEAD
<<<<<<< HEAD
=======

def enable_permissions_by_default():
    settings = frappe.get_single("Insights Settings")
    if not settings.enable_permissions:
        settings.enable_permissions = 1
        settings.save(ignore_permissions=True)
>>>>>>> 2de27f32 (fix: enable permissions by default after migration)
=======
>>>>>>> c4ef014e (fix: revert changes)
