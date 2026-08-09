# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Whose permissions filter a chart's rows at execution.

The authority is declared on the content document (`data_authority` on
`Insights Chart v3`) and read here. A request names the chart, the chart names
the authority — there is deliberately no way to pass an authority or a user in
from the wire.

`Viewer` is the engine's native permission application: the session user.
`Author` applies the document owner's permission context instead, without ever
switching the session user.
"""

from contextlib import contextmanager

import frappe

VIEWER = "Viewer"
AUTHOR = "Author"


def get_authority_user() -> str:
    """The user whose permissions the engine applies to the rows it is fetching."""
    return getattr(frappe.local, "insights_authority_user", None) or frappe.session.user


def has_declared_authority() -> bool:
    """True while execution runs under an authority declared by a content document."""
    return bool(getattr(frappe.local, "insights_authority_user", None))


def get_authority_user_for(doctype: str, name: str | None) -> str:
    """The authority user declared by the stored `doctype`/`name` document.

    Read straight from the database, never from an in-memory document: `run_doc_method`
    builds the document out of the request payload, so a caller could otherwise hand us
    its own `data_authority` and `owner`.
    """
    declaration = (
        frappe.db.get_value(doctype, name, ["data_authority", "owner"], as_dict=True) if name else None
    )
    if not declaration:
        # unsaved content — the author is whoever is building it
        return frappe.session.user

    if (declaration.data_authority or VIEWER) == AUTHOR:
        return declaration.owner

    return frappe.session.user


@contextmanager
def data_authority_of(doc):
    """Run the enclosed execution under the authority `doc` declares."""
    user = get_authority_user_for(doc.doctype, doc.name)
    previous = getattr(frappe.local, "insights_authority_user", None)
    frappe.local.insights_authority_user = user
    try:
        yield user
    finally:
        frappe.local.insights_authority_user = previous
