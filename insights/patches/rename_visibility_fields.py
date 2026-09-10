import frappe
from frappe.model.utils.rename_field import rename_field

CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"
VISIBILITY_DOCTYPES = (CHART, DASHBOARD)


def execute():
    """Carry the fields this branch renamed on a site that ran their first bodies.

    Nothing is released, so `set_visibility_from_is_public` and
    `name_author_at_public_rung` were rewritten to the new names rather than
    given successors. A site that already ran them still holds the old columns,
    and this is what moves them.

    It runs after those two because both are no-ops for these columns on a fresh
    site - the old columns do not exist there - so nothing this patch copies can
    land on a value they wrote.
    """
    if frappe.db.has_column(DASHBOARD, "slug"):
        rename_field(DASHBOARD, "slug", "route")

    if frappe.db.has_column(CHART, "data_authority"):
        # not a rename: a Select of two words becomes a Check, so the copy is
        # the mapping. The new column's default already says 1 ("Viewer")
        chart = frappe.qb.DocType(CHART)
        frappe.qb.update(chart).set(chart.apply_user_permissions, 0).where(
            chart.data_authority == "Author"
        ).run()

    for doctype in VISIBILITY_DOCTYPES:
        content = frappe.qb.DocType(doctype)
        frappe.qb.update(content).set(content.visibility, "Roles").where(
            content.visibility == "Specific Roles"
        ).run()
