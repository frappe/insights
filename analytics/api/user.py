# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_user_info():
    users = frappe.db.get_all(
        "User", fields=["name", "email", "user_image", "full_name", "user_type"]
    )
    out = {}
    for user in users:
        if frappe.session.user == user.name:
            user.session_user = True
        out[user.name] = user
    return out
