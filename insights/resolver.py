# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Turns a content reference into a site-local document name.

A reference is what a consumer app, a desk route or a bookmark carries. Four
forms are accepted for a dashboard, three for a chart:

    Standard ID  `{app}/{name}`  the identity of shipped content, the field
                                 standard content sync writes; the only form
                                 that crosses the contract boundary
    docname      the hash primary key, site-local
    slug         the cosmetic, human-readable dashboard key
    v2 name      the primary key this document carried before the rename to v3,
                 kept in `old_name` so a link shared back then still opens

The forms are discriminated by shape, not by trying every lookup and hoping:

    a Standard ID contains a slash — no other form ever does
    a docname is an existing primary key
    a slug is neither

So the precedence is: slash -> Standard ID, exclusively. Otherwise docname
first, then slug, then the v2 name. A slug that happens to equal another
dashboard's hash name resolves to that dashboard — internal identity wins, and
nothing internal references a slug anyway.

A Standard ID resolves to the standard document, always. A duplicate of shipped
content is an ordinary user document with its own identity and is never handed
back for the id it was copied from.
"""

import frappe
from frappe import _

DASHBOARD = "Insights Dashboard v3"
CHART = "Insights Chart v3"

# The doctypes this resolver serves, and whether they carry a slug. Charts are
# mounted by Standard ID or docname only. Queries are addressed by name from
# inside a chart, never from outside, so they are absent by design.
RESOLVABLE_DOCTYPES = {
    DASHBOARD: True,
    CHART: False,
}


class ContentNotAvailableError(frappe.PermissionError):
    """Raised by `resolve_for_read` when a reference names nothing, and when it
    names something the user may not read. One type, one message, so a caller
    cannot tell the two apart and the resolver leaks no existence information.
    """


def resolve(doctype: str, reference: str) -> str | None:
    """Return the document name a reference points at, or None.

    A pure lookup: it applies the standard-document policy but checks no
    permission. Server-side callers that have already established access
    (standard content sync, migrations, admin tooling) use this. Anything
    answering a user request uses `resolve_for_read`.
    """
    if doctype not in RESOLVABLE_DOCTYPES:
        raise ValueError(f"{doctype} cannot be resolved by reference")

    reference = (reference or "").strip()
    if not reference:
        return None

    if "/" in reference:
        return _by_standard_id(doctype, reference)

    return _by_docname(doctype, reference) or _by_slug(doctype, reference) or _by_old_name(doctype, reference)


def resolve_for_read(doctype: str, reference: str) -> str:
    """Return the document name a reference points at, for a user who may read it.

    Raises `ContentNotAvailableError` if the reference resolves to nothing or to
    a document the current user cannot read. Both cases produce the identical
    error, which is the whole point: a viewer endpoint built on this cannot be
    used to probe what exists on the site.
    """
    name = resolve(doctype, reference)
    if not name or not frappe.has_permission(doctype, ptype="read", doc=name):
        frappe.throw(_("This content is not available"), exc=ContentNotAvailableError)

    return name


def _by_standard_id(doctype: str, reference: str) -> str | None:
    # is_standard is part of the key, not a filter on the result: a user copy
    # carries the Standard ID it was duplicated from, and must never answer for it
    return frappe.db.get_value(
        doctype,
        {"standard_id": reference, "is_standard": 1},
        "name",
        order_by="creation asc",
    )


def _by_docname(doctype: str, reference: str) -> str | None:
    return frappe.db.exists(doctype, reference)


def _by_slug(doctype: str, reference: str) -> str | None:
    if not RESOLVABLE_DOCTYPES[doctype]:
        return None

    # slugs are unique by construction (see the dashboard controller); the
    # ordering only keeps the answer stable if an old row ever escaped that
    return frappe.db.get_value(doctype, {"slug": reference}, "name", order_by="creation asc")


def _by_old_name(doctype: str, reference: str) -> str | None:
    # last, because a v2 name is history: a document that still answers to its
    # current name must never be reached through some other document's past
    return frappe.db.get_value(doctype, {"old_name": reference}, "name", order_by="creation asc")
