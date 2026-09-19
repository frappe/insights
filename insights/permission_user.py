# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Whose permissions filter the rows an execution returns.

The engine applies one user's permissions to the rows and columns it fetches.
Usually that is the caller. Two things make it somebody else.

Content declares it. `apply_user_permissions` on a chart, unchecked, hands the
rows to the owner - a reader of the chart sees what the owner would see - while
checked it names nobody and leaves the execution filtering by whoever it already
runs as. At the `Public` level the box can only be unchecked, which is what keeps
a guest read out of this module: `validate_public_permissions` in
`insights.permissions` is where that is settled.

An unattended execution names it. A public link (Guest), a dashboard preview
(Guest with a minted key) and the alert scheduler (Administrator) have no caller
at all, so each records a user at the moment the privileged act happened -
publishing a chart, minting a preview key, enabling an alert.

The session user never changes, so `frappe.set_user` and what it does to
`form_dict` and `sid` stay out of the request.

This answers "whose rows", never "may this caller act". An authorization check
reads `frappe.session.user`, the same as it always did.
"""

from contextlib import contextmanager

import frappe


def get_permission_user() -> str:
    """The user whose permissions the engine applies to the rows it fetches."""
    return getattr(frappe.local, "insights_permission_user", None) or frappe.session.user


@contextmanager
def permission_user(user: str):
    """Run the enclosed execution under `user`.

    An unattended execution has no reader to fall back on, so refusing an empty
    user is the only safe reading of it. Content that predates the field is
    named by `insights.patches.backfill_permission_user`.
    """
    if not user:
        frappe.throw(
            frappe._("This content does not name a user to run as."),
            frappe.PermissionError,
        )

    previous = getattr(frappe.local, "insights_permission_user", None)
    frappe.local.insights_permission_user = user
    try:
        yield user
    finally:
        frappe.local.insights_permission_user = previous


def permission_user_for(doc) -> str:
    """The user the stored `doc` runs as.

    An unchecked `apply_user_permissions` names the document owner. Checked, it
    names nobody, so the execution keeps whoever it already runs as - the reader
    at the keyboard, or the user a public link or an alert already named. There
    is deliberately no third answer, and no way to pass a user in from the wire.

    Read from the row, never from the document in hand: `run_doc_method` builds
    that one out of the request payload, so a caller could otherwise hand us its
    own `apply_user_permissions` and `owner`.
    """
    declared = (
        frappe.db.get_value(doc.doctype, doc.name, ["apply_user_permissions", "owner"], as_dict=True)
        if doc.name
        else None
    )
    if declared and not declared.apply_user_permissions:
        return declared.owner

    # A preview render has no caller: it arrives as Guest, and Guest sees
    # nothing, so the image would be a page of empty cards. The key names the
    # user it was minted for, and names them only for the documents that key
    # opens — the same scope the read grant uses.
    previewed = preview_user_for(doc)
    if previewed:
        return previewed

    # unsaved content included: the owner is whoever is building it
    return get_permission_user()


def preview_user_for(doc) -> str | None:
    """The user a preview render of `doc` draws as, or nothing outside a render."""
    # imported here because `insights.api` reaches back into this module
    from insights.api.shared import get_preview_key, is_being_previewed

    key = get_preview_key()
    if not key or not doc.name or not is_being_previewed(doc.doctype, doc.name):
        return None
    return key["user"]
