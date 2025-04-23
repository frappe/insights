# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


__version__ = "3.0.26"


def create_toast(
    message: str | None = None,
    title: str | None = None,
    type: str = "info",
    duration: int = 5,
):
    import frappe

    if not title:
        title = type.capitalize()

    frappe.publish_realtime(
        event="insights_notification",
        user=frappe.session.user,
        message={
            "message": message,
            "title": title,
            "type": type,
            "user": frappe.session.user,
            "duration": duration,
        },
    )


# for backward compatibility
def notify(*args, **kwargs):
    create_toast(*args, **kwargs)
