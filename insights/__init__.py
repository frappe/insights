# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

__version__ = "0.1.0-beta"


def notify(message: str, title=None, notification_type="info"):
    frappe.publish_realtime(
        event="insights_notification",
        message={
            "message": message,
            "title": title,
            "type": notification_type,
            "user": frappe.session.user,
        },
    )
