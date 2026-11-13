import frappe


def execute():
    """Delete the stored values of query variables that no longer exist. frappe
    deletes a deleted document's secrets and never a child row's, so a deleted
    script query, or a variable taken off one, left its value in `__Auth`."""
    Auth = frappe.qb.DocType("__Auth")
    Variable = frappe.qb.DocType("Insights Query Variable")
    (
        frappe.qb.from_(Auth)
        .delete()
        .where(Auth.doctype == "Insights Query Variable")
        .where(Auth.name.notin(frappe.qb.from_(Variable).select(Variable.name)))
        .run()
    )
