# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Whose permissions filter the rows an execution returns.

Three executions have no caller whose permissions can decide the rows: a public
link (Guest), a dashboard preview (Guest with a minted key), and the alert
scheduler (Administrator). Each one names a user instead, recorded on the
content at the moment the privileged act happened - publishing a chart, minting
a preview key, enabling an alert.

The engine then filters rows and columns by that user. The session user never
changes, so `frappe.set_user` and what it does to `form_dict` and `sid` stay out
of the request.

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

    An unattended execution has no viewer to fall back on, so refusing an empty
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
