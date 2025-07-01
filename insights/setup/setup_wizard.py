# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import os

import frappe
from frappe import _

from insights.setup.demo import DemoDataFactory


def get_setup_stages(args=None):
    return [
        {
            "status": _("Setting up demo data"),
            "fail_msg": _("Failed to setup demo data"),
            "tasks": [
                {
                    "fn": setup_demo_data,
                    "args": args,
                    "fail_msg": _("Failed to setup demo data"),
                }
            ],
        },
        {
            "status": _("Wrapping up"),
            "fail_msg": _("Failed to login"),
            "tasks": [{"fn": wrap_up, "args": args, "fail_msg": _("Failed to login")}],
        },
    ]


def setup_demo_data(args):
    if frappe.flags.in_test or os.environ.get("CI"):
        return
    factory = DemoDataFactory()
    factory.run()
    frappe.db.commit()


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


@frappe.whitelist()
def enable_setup_wizard_complete():
    frappe.db.set_value(
        "Installed Application",
        {"app_name": "insights"},
        "is_setup_complete",
        1,
    )
    frappe.clear_cache()
