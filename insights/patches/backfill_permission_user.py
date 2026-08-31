import frappe


def execute():
    """Name a user on content that was already publishing or alerting.

    A public execution and an alert both used to run with permission checks off,
    so nothing recorded whose rows they were showing. Without a name they now
    refuse to run. `owner` is the closest thing the row holds to the person who
    published it, so use it and leave the rest to a re-publish.
    """
    for doctype in ("Insights Chart v3", "Insights Dashboard v3"):
        table = frappe.qb.DocType(doctype)
        (
            frappe.qb.update(table)
            .set(table.permission_user, table.owner)
            .where((table.is_public == 1) & table.permission_user.isnull())
            .run()
        )

    alert = frappe.qb.DocType("Insights Alert")
    (
        frappe.qb.update(alert)
        .set(alert.permission_user, alert.owner)
        .where(alert.permission_user.isnull())
        .run()
    )
