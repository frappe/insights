import frappe

from insights.bundles import WORKBOOK


def execute():
    """Flag the workbooks an app ships as standard content.

    The container workbook already carried its identity — `29a1e82f` moved that
    off a site global and onto the document — but not the flag that says what
    the identity means. Sync now reconciles the workbook like every other
    document it ships, and `is_standard` is what that pass reads to find the
    ones it owns: without the flag, a workbook shipped by an earlier release is
    invisible to the reconcile, which would create a second one beside it.

    Identity is the whole test. A `logical_id` on a workbook is only ever
    written by sync, so a workbook that has one is shipped, and a workbook that
    does not is a site's own. Duplicates of shipped content are user workbooks
    and never carry it.

    Runs before the first sync on migrate, so the reconcile finds what is
    already there. A second run finds nothing left to flag.
    """
    shipped = frappe.get_all(
        WORKBOOK,
        filters={"logical_id": ("is", "set"), "is_standard": 0},
        pluck="name",
    )
    for name in shipped:
        frappe.db.set_value(WORKBOOK, name, "is_standard", 1, update_modified=False)

    if shipped:
        print(f"Insights: flagged {len(shipped)} shipped workbook(s) standard")
