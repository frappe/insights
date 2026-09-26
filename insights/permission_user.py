# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Whose permissions filter the rows an execution returns.

The engine applies one user's permissions to the rows and columns it fetches.
Usually that user is the caller. Two cases change it.

Content can declare it. With `run_as_owner` checked, a chart runs as its owner,
so a reader sees the rows the owner would see. Unchecked, it names nobody, and
the execution keeps its current user. At the `Public` level the box must be
checked, so a guest read always runs as the owner. `validate_run_as_owner` in
`insights.permissions` enforces that.

An unattended execution can name it. A dashboard preview (Guest with a minted
key) and the alert scheduler (Administrator) have no caller of their own. So
the key records the user it was minted for, and the alert records the user who
enabled it.

The session user never changes, so `frappe.set_user` and its effects on
`form_dict` and `sid` stay out of the request. A script is the one exception.
It reads through frappe, which checks the session, so `script_session` makes
the permission user the session user while the script runs.

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
    and both are restored. The rest of the request stays the caller's.
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
    """Run the enclosed execution as `doc` declares.

    It runs as the user `permission_user_for` names, and records `doc` as the
    declaring document. The Builder and the reader's card both enter here, so
    they agree about one chart.
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

    Only server code enters `runs_as`, with a row it chose. So this names a
    stored document, while a name on the document being built may come from the
    request body.
    """
    return getattr(frappe.local, "insights_declaring_document", None)


def permission_user_for(doc) -> str:
    """The user the stored `doc` runs as.

    With `run_as_owner` checked, it is the document owner, while the owner
    still decides it (`declared_owner`). Otherwise it names nobody, and the
    execution keeps its current user: the reader, or the user a public link or
    an alert already named. There is no third answer on purpose, and no way to
    pass a user in from the request.

    Read from the stored row, never from the document in hand. `run_doc_method`
    builds that document from the request payload, so a caller could otherwise
    send its own `run_as_owner` and `owner`.
    """
    owner = declared_owner(doc)
    if owner:
        return owner

    # A preview render has no caller. It arrives as Guest, and Guest sees
    # nothing, so the image would show only empty cards. The key names the
    # user it was minted for, but only for the documents that key opens. The
    # read grant uses the same scope.
    previewed = preview_user_for(doc)
    if previewed:
        return previewed

    # unsaved content included: the owner is whoever is building it
    return get_permission_user()


def declared_owner(doc) -> str | None:
    """The owner the stored `doc` runs as, or None while it runs as its reader.

    The owner decides only while `may_run_as` allows them. An owner the
    workbook no longer names, or a disabled one, gives nobody their rows. The
    box stays checked until an editor clears it.
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
    """Whether `user` still decides whose rows `doc` runs with: enabled, and with write on it.

    Checked for an alert's enabler before every send, and for a chart's owner
    before every run. A disabled account keeps its roles, so enabled is checked
    separately.
    """
    return bool(frappe.db.get_value("User", user, "enabled")) and bool(
        frappe.has_permission(doctype, ptype="write", doc=doc, user=user)
    )


def preview_user_for(doc) -> str | None:
    """The user a preview render of `doc` runs as, or None outside a render."""
    key = get_preview_key()
    if not key or not doc.name or not is_being_previewed(doc.doctype, doc.name):
        return None
    return key["user"]
