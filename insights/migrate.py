# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe


def after_migrate():
    enable_permissions_by_default()


def enable_permissions_by_default():
    settings = frappe.get_single("Insights Settings")
    if not settings.enable_permissions:
        settings.enable_permissions = 1
        settings.save()
        frappe.db.commit()
