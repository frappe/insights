import frappe

DOCTYPES = ("Insights Chart v3", "Insights Dashboard v3")


def execute():
    """
    The visibility ladder absorbs `is_public` as its top rung, so publicly
    shared charts and dashboards move to `visibility = "Public"`.

    `is_public` keeps its value and the shared pages keep reading it until the
    field retires with the template migration (ticket 23).
    """
    for doctype in DOCTYPES:
        content = frappe.qb.DocType(doctype)
        frappe.qb.update(content).set(content.visibility, "Public").where(content.is_public == 1).run()
