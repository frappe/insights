"""What a preview key opens.

Generating a dashboard's preview image starts a browser on this server and hands
it a key, because the dashboard it renders is usually not public. The key is a
read grant and nothing wider: it opens the documents the image already shows.
`insights.permissions` reads it as that grant, and `insights.permission_user`
reads the user it was cut for, so the render draws rows instead of empty cards.
"""

from contextlib import contextmanager

import frappe


def cache_key(key: str) -> str:
    return f"insights_preview_key:{key}"


@contextmanager
def generate_preview_key(dashboard: str):
    """A key that stands in for the reader of one dashboard, for one render.

    The key names its dashboard, so a leaked key reads that dashboard and the
    charts and queries on it — the same documents the preview image itself
    shows — and nothing else.

    It names its user too. The render arrives as Guest, so the rows it draws
    are filtered by the user the key was cut for, and the image shows what that
    user would see.
    """
    key = frappe.generate_hash()
    try:
        frappe.cache.set_value(cache_key(key), {"dashboard": dashboard, "user": frappe.session.user})
        yield key
    finally:
        frappe.cache.delete_value(cache_key(key))


def is_being_previewed(doctype: str, name: str):
    """Whether this document is part of the dashboard a preview key was cut for.

    The preview browser reads a dashboard, the charts on it and the queries
    behind those charts — the documents the image it produces already shows.
    The key opens those and stops there.
    """
    dashboard = get_previewed_dashboard()
    if not dashboard:
        return False
    if doctype == "Insights Dashboard v3":
        return name == dashboard

    charts = frappe.get_all(
        "Insights Dashboard Chart v3",
        filters={"parent": dashboard, "parenttype": "Insights Dashboard v3"},
        pluck="chart",
    )
    if doctype == "Insights Chart v3":
        return name in charts

    linked = frappe.get_all("Insights Chart v3", filters={"name": ["in", charts]}, pluck="query")
    return name in linked


def get_preview_key():
    key = frappe.request and frappe.request.headers.get("X-Insights-Preview-Key")
    if not key:
        return None
    return frappe.cache.get_value(cache_key(key))


def get_previewed_dashboard():
    key = get_preview_key()
    return key["dashboard"] if key else None
