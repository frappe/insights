import frappe
from frappe import _


def block_standard_edits(doc, method=None):
    if not doc.get("is_standard"):
        return
    if doc.flags.in_bundle_sync or frappe.conf.developer_mode:
        return
    if doc.is_new():
        return
    frappe.throw(_("Standard content is read-only. Duplicate it to make changes."))


def block_standard_deletes(doc, method=None):
    if not doc.get("is_standard"):
        return
    if doc.flags.in_bundle_sync or frappe.conf.developer_mode:
        return
    frappe.throw(_("Standard content is read-only. It is removed when its app is uninstalled."))


def before_app_uninstall(app_name):
    # filled in by bundle sync: delete the app's standard docs, spare user copies
    pass
