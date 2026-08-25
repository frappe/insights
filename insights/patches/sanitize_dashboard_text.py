import frappe
from frappe.utils.html_utils import sanitize_html


def execute():
    """Sanitize the text items already stored on every dashboard.

    `items` is a JSON field, so nothing sanitized what was written into it
    before the doctype started doing so. A dashboard is rendered from what is
    stored, so the stored markup is the one that matters.
    """
    dashboards = frappe.get_all(
        "Insights Dashboard v3",
        filters={"items": ["is", "set"]},
        fields=["name", "items"],
    )
    for dashboard in dashboards:
        # `dashboard.items` would resolve to the dict method
        items = frappe.parse_json(dashboard["items"]) or []
        sanitized = False
        for item in items:
            if item.get("type") != "text" or not item.get("text"):
                continue
            clean = sanitize_html(item["text"], always_sanitize=True)
            sanitized = sanitized or clean != item["text"]
            item["text"] = clean

        if sanitized:
            frappe.db.set_value(
                "Insights Dashboard v3",
                dashboard.name,
                "items",
                frappe.as_json(items),
                update_modified=False,
            )
