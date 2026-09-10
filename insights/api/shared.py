"""What a preview key opens.

Generating a dashboard's preview image starts a browser on this server and hands
it a key, because the dashboard it renders is usually not public. The key is a
read grant and nothing wider: it opens the documents the image already shows.
`insights.permissions` reads it as that grant, and `insights.permission_user`
reads the user it was cut for, so the render draws rows instead of empty cards.
"""

import frappe


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
    return frappe.cache.get_value(f"insights_preview_key:{key}")


def get_previewed_dashboard():
    key = get_preview_key()
    return key["dashboard"] if key else None
