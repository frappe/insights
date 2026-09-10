# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Turns a content reference into a site-local document name.

A reference is what a consumer app, a desk route or a bookmark carries. Three
forms are accepted for a dashboard, two for a chart:

    docname      the hash primary key, site-local
    route        the cosmetic, human-readable dashboard key
    v2 name      the primary key this document carried before the rename to v3,
                 kept in `old_name` so a link shared back then still opens

The forms are discriminated by shape, not by trying every lookup and hoping: a
docname is an existing primary key, a route is not. So the precedence is docname
first, then route, then the v2 name. A route that happens to equal another
dashboard's hash name resolves to that dashboard — internal identity wins, and
nothing internal references a route anyway.
"""

import frappe
from frappe import _

DASHBOARD = "Insights Dashboard v3"
CHART = "Insights Chart v3"

# The doctypes this resolver serves, and whether they carry a route. Charts are
# mounted by docname only. Queries are addressed by name from inside a chart,
# never from outside, so they are absent by design.
RESOLVABLE_DOCTYPES = {
    DASHBOARD: True,
    CHART: False,
}


def resolve(doctype: str, reference: str) -> str | None:
    """Return the document name a reference points at, or None.

    A pure lookup: it checks no permission. Server-side callers that have
    already established access (standard content sync, migrations, admin
    tooling) use this. Anything answering a user request uses `resolve_for_read`.
    """
    if doctype not in RESOLVABLE_DOCTYPES:
        raise ValueError(f"{doctype} cannot be resolved by reference")

    reference = (reference or "").strip()
    if not reference:
        return None

    return (
        _by_docname(doctype, reference) or _by_route(doctype, reference) or _by_old_name(doctype, reference)
    )


def resolve_for_read(doctype: str, reference: str) -> str:
    """Return the document name a reference points at, for a user who may read it.

    Raises `frappe.DoesNotExistError` if the reference resolves to nothing or to
    a document the current user cannot read. Both cases produce the identical
    error, which is the whole point: a read endpoint built on this cannot be
    used to probe what exists on the site.
    """
    name = resolve(doctype, reference)
    if not name or not frappe.has_permission(doctype, ptype="read", doc=name):
        frappe.throw(_("Not Found"), exc=frappe.DoesNotExistError)

    return name


def _by_docname(doctype: str, reference: str) -> str | None:
    return frappe.db.exists(doctype, reference)


def _by_route(doctype: str, reference: str) -> str | None:
    if not RESOLVABLE_DOCTYPES[doctype]:
        return None

    # routes are unique by construction (see the dashboard controller); the
    # ordering only keeps the answer stable if an old row ever escaped that
    return frappe.db.get_value(doctype, {"route": reference}, "name", order_by="creation asc")


def _by_old_name(doctype: str, reference: str) -> str | None:
    # last, because a v2 name is history: a document that still answers to its
    # current name must never be reached through some other document's past
    return frappe.db.get_value(doctype, {"old_name": reference}, "name", order_by="creation asc")
