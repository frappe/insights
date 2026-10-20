import frappe

from insights.patches.run_public_charts_as_owner import why_query_rows_differ
from insights.permission_user import may_run_as
from insights.permissions import workbook_of
from insights.upgrade import add_item

ALERT = "Insights Alert"
WORKBOOK = "Insights Workbook"


def execute():
    """Run an alert as its workbook's owner where its enabler may not.

    Insights 3 sent an alert as whoever turned it on. Insights 4 also needs that
    user to edit the alert's workbook, and stops the alert at its next run
    otherwise. After the shares above, an enabler who made something in the
    workbook can. One who cannot would stop a running alert, so it runs as the
    workbook's owner when the owner reads the same rows: the enabler chose its
    recipients, and the owner's rows are not theirs to send. Otherwise it is
    reported before it stops.
    """
    for alert in frappe.get_all(
        ALERT,
        filters={"disabled": 0},
        fields=["name", "title", "query", "condition", "permission_user"],
    ):
        enabler = alert.permission_user
        if enabler and may_run_as(ALERT, alert.name, enabler):
            continue

        workbook = workbook_of(frappe._dict(alert, doctype=ALERT))
        owner = workbook and frappe.db.get_value(WORKBOOK, workbook, "owner")
        add_item("P19", move_or_report(alert, enabler, owner), reference=(ALERT, alert.name))


def move_or_report(alert, enabler: str | None, owner: str | None) -> str:
    """Move the alert to `owner` where that keeps its rows. The message says which happened."""
    title = alert.title
    if not enabler:
        return f'"{title}" has no user to run as, so it stops at its next run'

    if not owner or not may_run_as(ALERT, alert.name, owner):
        return f'"{title}" stops at its next run: neither {enabler} nor the workbook\'s owner can edit it'

    if why := why_query_rows_differ(alert.query, {"expression": alert.condition}, (enabler, owner)):
        return (
            f'"{title}" stops at its next run: {enabler}, who turned it on, can\'t edit the workbook. It '
            f"{why}, so {owner}, who owns the workbook, may see other rows."
        )

    frappe.db.set_value(ALERT, alert.name, "permission_user", owner, update_modified=False)
    return f'"{title}" now runs as {owner}, who owns the workbook, in place of {enabler}, with the same rows'
