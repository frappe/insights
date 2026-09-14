import frappe


def execute():
    """Every dashboard saved before the compact layout became the dashboard's
    own field drew with its gaps closed, so every one of them keeps doing that.

    The setting used to live in the browser and was on unless a reader turned it
    off. The field that replaced it was added in the v2 era and nothing has ever
    written it, so every stored row holds 0 — and a deploy alone would open the
    gaps in every saved dashboard. The field's default is 1 for the same reason.

    `modified` stays where the author left it: this restores the layout they
    already had rather than editing their dashboard.
    """
    frappe.reload_doc("insights", "doctype", "insights_dashboard_v3")
    frappe.db.set_value(
        "Insights Dashboard v3",
        {"vertical_compact_layout": 0},
        "vertical_compact_layout",
        1,
        update_modified=False,
    )
