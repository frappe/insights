# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The User Permissions that narrowed the rows an execution returned.

A narrowed number looks like the total. A Sales User limited to Territory North
sees "Revenue" and takes it for the company's. So the card says which
permissions narrowed it. See `docs/adr/a-reader-never-sees-a-false-empty.md`.

Only a real User Permission record is named. A role's match condition also
narrows the rows, but it names no document, so there is nothing to show.
Insights' own narrowing, a team's Table Restriction on another source, names
nothing either, so the card says only that the reader's permissions narrowed
it. Desk's own row narrowing never sets this mark.

Every entry records the user it applied to, because an execution does not
always run as the reader. A Public chart runs as its owner, and an alert as the
user who enabled it. Their User Permissions name documents (a customer, a
company, a territory) that the reader was never shown, and they are not the
reader's restriction. So the record is read back for one user, and an
execution that ran as another user reports nothing to this one.

Recorded where the row filter is built, because only that code knows what
frappe applied. Read back after the query runs.
"""

import frappe
from frappe.model.db_query import requires_owner_constraint

APPLIED = "insights_applied_user_permissions"
# the users a team's Table Restriction narrowed this build for
NARROWED = "insights_narrowed_by_permissions"


def forget() -> None:
    """Clear the last build's records, so one build never reports for another."""
    setattr(frappe.local, APPLIED, {})
    setattr(frappe.local, NARROWED, set())


def record_narrowed(user: str) -> None:
    """Record that a restriction narrowed the rows or cells this build returned for `user`."""
    narrowed_for = getattr(frappe.local, NARROWED, None)
    if narrowed_for is None:
        narrowed_for = set()
        setattr(frappe.local, NARROWED, narrowed_for)
    narrowed_for.add(user)


def record(user: str, match_filters: dict[str, list[str]]) -> None:
    """Merge one of frappe's `DatabaseQuery.match_filters` entries, for the user
    the build applied it to."""
    applied_for = getattr(frappe.local, APPLIED, None)
    if applied_for is None:
        applied_for = {}
        setattr(frappe.local, APPLIED, applied_for)
    for doctype, documents in (match_filters or {}).items():
        applied_for.setdefault(user, {}).setdefault(doctype, set()).update(documents)


def narrowing(doctype: str, user: str, parent_doctype: str | None = None) -> dict[str, list[str]]:
    """The User Permissions frappe applies to a list of `doctype` for `user`.

    Frappe records this as `DatabaseQuery.match_filters`, but only its legacy
    query implementation sets it, and `frappe.get_list` no longer uses that
    one. This reads the same answer from the public `get_user_permissions`, so
    every chart's row filter stays on `get_list`. The supported path should
    report what it applied; that is a change for frappe.

    It reads the doctype frappe checks, the way frappe reads it: every Link
    field of that doctype, plus the doctype itself as `name`, minus the fields
    that opt out. Frappe checks a child table against its parent
    (`permission_doctype = parent_doctype or doctype`) and ignores the child's
    own links. So a User Permission on a field only the parent links narrows
    the rows, and one on a field only the child links narrows nothing.
    """
    permission_doctype = parent_doctype or doctype

    held = frappe.permissions.get_user_permissions(user)
    if not held:
        return {}

    # frappe skips User Permissions in these two cases and narrows by owner or
    # by shares instead. Naming them would blame the reader's restriction for
    # a narrowing it did not cause
    role_permissions = frappe.permissions.get_role_permissions(permission_doctype, user=user)
    if not (role_permissions.get("read") or role_permissions.get("select")):
        return {}
    if requires_owner_constraint(role_permissions):
        return {}

    meta = frappe.get_meta(permission_doctype)
    links = [*meta.get_link_fields(), frappe._dict(options=permission_doctype, fieldname="name")]

    narrowed: dict[str, list[str]] = {}
    for field in links:
        if field.get("ignore_user_permissions"):
            continue

        # a User Permission applies only to the doctype in its `applicable_for`,
        # or to every doctype when that is empty
        documents = [
            permission["doc"]
            for permission in held.get(field.get("options")) or []
            if permission.get("applicable_for") in (None, "", permission_doctype)
        ]
        if documents:
            narrowed[field.get("options")] = documents

    return narrowed


def scope(user: str) -> dict:
    """What narrowed this execution for `user`, in the shape a card's answer includes.

    `user_permissions` has one entry per doctype, in a stable order.
    `narrowed_by_permissions` marks a narrowing with nothing to name. Empty
    when nothing narrowed it, so the card shows no scope.
    """
    recorded = (getattr(frappe.local, APPLIED, None) or {}).get(user) or {}
    answer = {}
    if recorded:
        answer["user_permissions"] = [
            {"doctype": doctype, "documents": sorted(recorded[doctype])} for doctype in sorted(recorded)
        ]
    if user in (getattr(frappe.local, NARROWED, None) or set()):
        answer["narrowed_by_permissions"] = True
    return answer
