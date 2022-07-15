# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def after_install():
    create_roles()
    frappe.db.commit()


def create_roles():
    frappe.get_doc(
        {
            "doctype": "Role",
            "role_name": "Insights User",
            "home_page": "/insights",
        }
    ).insert(ignore_if_duplicate=True)
