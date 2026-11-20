import frappe

DOCTYPES = ("Insights Chart v3", "Insights Dashboard v3")


def execute():
    """
    `visibility` absorbs `is_public` as its widest level, so publicly shared
    charts and dashboards move to `visibility = "Public"`.

    This is the whole migration off `is_public`: nothing reads the field any
    more, and its column is left for `bench trim-tables`.
    """
    for doctype in DOCTYPES:
        # Sites upgrading straight from Insights v2 create these tables from the
        # current schema, which no longer has `is_public`: nothing to migrate.
        if not frappe.db.has_column(doctype, "is_public"):
            continue
        content = frappe.qb.DocType(doctype)
        frappe.qb.update(content).set(content.visibility, "Public").where(content.is_public == 1).run()
