# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Whose permissions filter the rows an execution returns.

The engine applies one user's permissions to the rows and columns it fetches.
Usually that is the caller. Two things make it somebody else.

Content declares it. `run_as_owner` on a chart, checked, hands the rows to the
owner - a reader of the chart sees what the owner would see - while unchecked it
names nobody and leaves the execution filtering by whoever it already runs as.
At the `Public` level the box can only be checked, which is what keeps a guest
read out of this module: `validate_run_as_owner` in `insights.permissions`
is where that is settled.

An unattended execution names it. A dashboard preview (Guest with a minted
key) and the alert scheduler (Administrator) have no caller of their own, so
the key records the user it was minted for and the alert the user who enabled
it.

The session user never changes, so `frappe.set_user` and what it does to
`form_dict` and `sid` stay out of the request. A script is the one exception:
it reads through frappe, which asks the session, so `script_session` hands the
session to the permission user for the length of the script.

This answers "whose rows", never "may this caller act". An authorization check
reads `frappe.session.user`, the same as it always did.
"""

from contextlib import contextmanager

import frappe

from insights.preview_key import get_preview_key, is_being_previewed


def get_permission_user() -> str:
    """The user whose permissions the engine applies to the rows it fetches."""
    return getattr(frappe.local, "insights_permission_user", None) or frappe.session.user


@contextmanager
def permission_user(user: str):
    """Run the enclosed execution under `user`.

    An unattended execution has no reader to fall back on, so refusing an empty
    user is the only safe reading of it.
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


@contextmanager
def script_session():
    """Run the enclosed script with the permission user as the session user.

    Only the user and the `UserPermissions` frappe caches for it are swapped,
    and both are put back: the rest of the request is still the caller's.
    """
    user = get_permission_user()
    session = frappe.local.session
    if session.user == user:
        yield
        return

    previous = session.user, frappe.local.user_perms
    session.user, frappe.local.user_perms = user, None
    try:
        yield
    finally:
        session.user, frappe.local.user_perms = previous


@contextmanager
def runs_as(doc):
    """Run the enclosed execution the way `doc` declares it.

    Under the user `permission_user_for` names, with `doc` recorded as the
    document that declared the execution. One entry point, so the builder and
    the reader's card agree about one chart.
    """
    previous = getattr(frappe.local, "insights_declaring_document", None)
    frappe.local.insights_declaring_document = frappe._dict(doctype=doc.doctype, name=doc.name)
    try:
        with permission_user(permission_user_for(doc)):
            yield
    finally:
        frappe.local.insights_declaring_document = previous


def declaring_document():
    """The document whose declaration the running execution entered, if any.

    Only server code enters `runs_as`, with a row it chose, so this names a
    stored document where a name on the document being built may be the
    request body's.
    """
    return getattr(frappe.local, "insights_declaring_document", None)


def permission_user_for(doc) -> str:
    """The user the stored `doc` runs as.

    A checked `run_as_owner` names the document owner while the owner still
    decides it (`declared_owner`). Otherwise it names nobody, so the execution
    keeps whoever it already runs as - the reader at the keyboard, or the user
    a public link or an alert already named. There is deliberately no third
    answer, and no way to pass a user in from the wire.

    Read from the row, never from the document in hand: `run_doc_method` builds
    that one out of the request payload, so a caller could otherwise hand us its
    own `run_as_owner` and `owner`.
    """
    owner = declared_owner(doc)
    if owner:
        return owner

    # A preview render has no caller: it arrives as Guest, and Guest sees
    # nothing, so the image would be a page of empty cards. The key names the
    # user it was minted for, and names them only for the documents that key
    # opens — the same scope the read grant uses.
    previewed = preview_user_for(doc)
    if previewed:
        return previewed

    # unsaved content included: the owner is whoever is building it
    return get_permission_user()


def declared_owner(doc) -> str | None:
    """The owner the stored `doc` runs as, or nothing while it runs as its reader.

    They decide it only while `may_run_as` admits them. An owner the workbook
    no longer names, or a disabled one, serves nobody their rows, and the box
    stays for an editor to take off.
    """
    declared = (
        frappe.db.get_value(doc.doctype, doc.name, ["run_as_owner", "owner"], as_dict=True)
        if doc.name
        else None
    )
    if declared and declared.run_as_owner and may_run_as(doc.doctype, doc.name, declared.owner):
        return declared.owner
    return None


def may_run_as(doctype: str, doc, user: str) -> bool:
    """Whether `user` still decides whose rows `doc` runs with: enabled, and a writer of it.

    Asked of an alert's enabler before every send, and of a chart's owner before
    every run. A disabled account keeps its roles, so it is asked on its own.
    """
    return bool(frappe.db.get_value("User", user, "enabled")) and bool(
        frappe.has_permission(doctype, ptype="write", doc=doc, user=user)
    )


def preview_user_for(doc) -> str | None:
    """The user a preview render of `doc` draws as, or nothing outside a render."""
    key = get_preview_key()
    if not key or not doc.name or not is_being_previewed(doc.doctype, doc.name):
        return None
    return key["user"]
