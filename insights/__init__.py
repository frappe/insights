# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from importlib.util import find_spec
from typing import TYPE_CHECKING

__version__ = "3.14.4"

if TYPE_CHECKING:
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import Warehouse

    warehouse: Warehouse
    db_connections: dict

__all__ = ["create_toast", "db_connections", "desk_islands", "notify", "warehouse"]


def desk_islands() -> bool:
    """Whether Frappe mounts islands on desk pages. Insights draws its charts and
    dashboards in desk with them, and stays out of desk on a Frappe without.

    A module is checked, not a System Settings field, because `hooks.py` reads
    it at import.
    """
    return find_spec("frappe.utils.island") is not None


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
