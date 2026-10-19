import frappe
from frappe.share import add_docshare

from insights.decorators import insights_whitelist
from insights.permissions import validate_shareable_users
from insights.upgrade import ITEM, get_item, mark_seen, open_item_filters


@insights_whitelist()
def get_upgrade_items():
    items = frappe.get_all(
        ITEM,
        filters=open_item_filters(),
        fields=["name", "code", "message", "reference_doctype", "reference_name", "user", "action"],
        order_by="code asc, creation asc",
    )
    # an app uninstalled since the upgrade took the doctype an item names
    gone = {
        doctype
        for doctype in {item.reference_doctype for item in items if item.reference_doctype}
        if not frappe.db.exists("DocType", doctype)
    }
    items = [item for item in items if item.reference_doctype not in gone]
    for item in items:
        item.workbook = reference_workbook(item)
        item.can_fix = can_fix(item)
    return items


def can_fix(item) -> bool:
    """Whether the session user holds the permission the item's fix needs."""
    if item.action == "open_settings":
        return bool(frappe.has_permission("Insights Settings", "write"))
    if item.action == "delete_workbook" or (item.action == "share_workbook" and item.user):
        ptype = "share" if item.action == "share_workbook" else "delete"
        return bool(frappe.has_permission("Insights Workbook", ptype, doc=item.reference_name))
    return False


def reference_workbook(item) -> str | None:
    """The workbook the app opens the reference in: a query, chart or dashboard
    has its own route under its workbook."""
    if item.reference_doctype == "Insights Workbook":
        return item.reference_name
    if item.reference_doctype and frappe.get_meta(item.reference_doctype).has_field("workbook"):
        return frappe.db.get_value(item.reference_doctype, item.reference_name, "workbook")


@insights_whitelist(methods=["POST"])
def mark_upgrade_seen():
    mark_seen()


@insights_whitelist(methods=["POST"])
def dismiss_upgrade_item(name: str):
    item = get_item(name)
    item.db_set("status", "Dismissed")


@insights_whitelist(methods=["POST"])
def fix_upgrade_item(name: str):
    """Apply the item's fix with the session user's own permission on its reference."""
    item = get_item(name)
    if item.action == "share_workbook" and item.user:
        validate_shareable_users({item.user})
        # checks the session user may share the workbook
        add_docshare("Insights Workbook", item.reference_name, user=item.user, write=1)
    elif item.action == "delete_workbook":
        frappe.delete_doc("Insights Workbook", item.reference_name)
    else:
        frappe.throw(frappe._("This item has no fix to apply."))
    # a save would check the reference, which the fix may have deleted
    item.db_set("status", "Done")
