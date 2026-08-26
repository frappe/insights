# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

__version__ = "3.3.1"

if TYPE_CHECKING:
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import Warehouse

    warehouse: Warehouse
    db_connections: dict

__all__ = ["create_toast", "db_connections", "notify", "warehouse"]


def __getattr__(name):
    if name == "warehouse":
        import frappe

        if not hasattr(frappe.local, "insights_warehouse"):
            from insights.insights.doctype.insights_data_source_v3.data_warehouse import Warehouse

            frappe.local.insights_warehouse = Warehouse()

        return frappe.local.insights_warehouse

    if name == "db_connections":
        import frappe

        if not hasattr(frappe.local, "insights_db_connections"):
            frappe.local.insights_db_connections = {}

        return frappe.local.insights_db_connections

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def create_toast(
    message: str | None = None,
    title: str | None = None,
    type: str = "info",
    duration: int = 5,
):
    """Publish a toast. The client renders it as text, so it leaves as text.

    Markup here reaches the reader as visible tags, and a value the caller
    interpolated would reach it as markup. Stripping is done once, here, rather
    than trusted at each of the places that raise a toast.
    """
    import frappe
    from frappe.utils import strip_html

    if not title:
        title = type.capitalize()

    frappe.publish_realtime(
        event="insights_notification",
        user=frappe.session.user,
        message={
            "message": strip_html(message) if message else message,
            "title": strip_html(title) if title else title,
            "type": type,
            "user": frappe.session.user,
            "duration": duration,
        },
    )


# for backward compatibility
def notify(*args, **kwargs):
    create_toast(*args, **kwargs)
