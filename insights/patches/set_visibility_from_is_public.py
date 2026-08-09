import frappe

DOCTYPES = ("Insights Chart v3", "Insights Dashboard v3")


def execute():
    """
    The visibility ladder absorbs `is_public` as its top rung, so publicly
    shared charts and dashboards move to `visibility = "Public"`.

    This is the whole migration off `is_public`: nothing reads the field any
    more. It keeps its value only because dropping a column is a separate act
    from ending its use, and this patch is what the drop will depend on.
    """
    for doctype in DOCTYPES:
        content = frappe.qb.DocType(doctype)
        frappe.qb.update(content).set(content.visibility, "Public").where(content.is_public == 1).run()
