import frappe


def execute():
    """Template ids are now qualified by their source app ("insights/sales")
    instead of bare folder names, so two apps can't collide and imported-state
    lookup has a stable key. Prefix any legacy bare `from_template` value with
    "insights/" — the bundled ERPNext templates were the only ones that ever
    shipped, so they all belong to insights."""
    rows = frappe.get_all(
        "Insights Workbook",
        filters={"from_template": ["!=", ""]},
        fields=["name", "from_template"],
    )
    for row in rows:
        if row.from_template and "/" not in row.from_template:
            frappe.db.set_value(
                "Insights Workbook",
                row.name,
                "from_template",
                f"insights/{row.from_template}",
                update_modified=False,
            )
