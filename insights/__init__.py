# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import importlib.metadata

__version__ = importlib.metadata.version(__name__)


def notify(*args, **kwargs):
    import frappe

    if len(args) == 1:
        kwargs["message"] = args[0]

    frappe.publish_realtime(
        event="insights_notification",
        user=frappe.session.user,
        message={
            "message": kwargs.get("message"),
            "title": kwargs.get("title"),
            "type": kwargs.get("type", "success"),
            "user": frappe.session.user,
        },
    )
