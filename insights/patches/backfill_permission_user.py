import frappe


def execute():
    """Name a user on an alert that was already running.

    An alert used to run with permission checks off, so nothing recorded whose
    rows it was showing. Without a name it now refuses to run. `owner` is the
    closest thing the row holds to the person who enabled it.
    """
    alert = frappe.qb.DocType("Insights Alert")
    (
        frappe.qb.update(alert)
        .set(alert.permission_user, alert.owner)
        .where(alert.permission_user.isnull())
        .run()
    )
