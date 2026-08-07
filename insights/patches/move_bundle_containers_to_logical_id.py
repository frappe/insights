import frappe

# what `insights.bundles` used to key a container workbook by
CONTAINER_KEY = "insights_bundle_workbook:"


def execute():
    """Move a bundle's container workbook identity off a site global and onto the
    workbook, as `standard_id`.

    The global was read through `frappe.db.get_global`, which serves defaults out
    of a cross-process cache with no invalidation guarantee. A read could miss the
    row the same transaction had just written, and sync then made a second
    container and rewrote every shipped document into it. The identity now lives
    on the document, so one transaction writes both and a rollback drops both.

    The recorded container keeps the bundle. A duplicate an earlier sync left
    behind is not adopted here: it is a plain workbook, and the next sync moves
    the documents back to the recorded one.

    The file name still says `logical_id`, the field's name when this was
    written. Renaming a registered patch file is asking for it to run again.
    """
    rows = frappe.get_all(
        "DefaultValue",
        filters={"parent": "__global", "defkey": ("like", f"{CONTAINER_KEY}%")},
        fields=["defkey", "defvalue"],
    )
    for row in rows:
        bundle_key = row.defkey[len(CONTAINER_KEY) :]
        if row.defvalue and frappe.db.exists("Insights Workbook", row.defvalue):
            frappe.db.set_value(
                "Insights Workbook", row.defvalue, "standard_id", bundle_key, update_modified=False
            )
        frappe.defaults.clear_default(key=row.defkey, parent="__global")
