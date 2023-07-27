# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _


def get_setup_stages(args=None):
    return [
        {
            "status": _("Wrapping up"),
            "fail_msg": _("Failed to login"),
            "tasks": [{"fn": wrap_up, "args": args, "fail_msg": _("Failed to login")}],
        }
    ]


def wrap_up(args):
    frappe.local.message_log = []
    set_user_as_insights_admin(args)
    login_as_first_user(args)


def set_user_as_insights_admin(args):
    # if developer mode is enabled, first user step is skipped, hence no user is created
    if not args.get("email") or not frappe.db.exists("User", args.get("email")):
        return
    user = frappe.get_doc("User", args.get("email"))
    user.add_roles("Insights Admin", "Insights User")


def login_as_first_user(args):
    if args.get("email") and hasattr(frappe.local, "login_manager"):
        frappe.local.login_manager.login_as(args.get("email"))
