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
from frappe.permissions import has_user_permission

from insights.not_permitted import has_permitted_chart
from insights.permissions import has_doc_permission

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

    A dashboard is also read as Not Found when every chart on it is Not
    Permitted or unreadable — `has_permitted_chart` answers that without running
    any of them.
    It is the same read check and so it belongs here, not above. A caller who
    may write the dashboard is not a reader of it and opens it whatever its
    charts answer: they are the one who can fix it.
    """
    name = resolve(doctype, reference)
    if not name or not may_read(frappe.get_doc(doctype, name)):
        not_found()

    # A dashboard every chart of which is Not Permitted holds nothing this reader
    # may see, and Not Found is the one answer for that too.
    if (
        doctype == DASHBOARD
        and not frappe.has_permission(DASHBOARD, ptype="write", doc=name)
        and not has_permitted_chart(name, frappe.session.user)
    ):
        not_found()

    return name


def not_found():
    """The one answer for content that does not exist and content the caller may not read."""
    frappe.throw(_("Not Found"), exc=frappe.DoesNotExistError)


def may_read(doc, user: str | None = None) -> bool:
    """Whether this reader may read this content. The whole question, once.

    A Frappe site answers it in two stacks and they can differ. The grants are
    the Insights controller's, asked here directly because frappe's role gate
    would need every reader, Guest included, to hold read on the doctype - a
    grant that would also open `/api/resource` to them.

    What the role gate also runs, and the controller does not, is the User
    Permission pass. A restriction on `Insights Dashboard v3`, or on the
    workbook it links, narrows `get_doc`, the list query and `can_write`. One
    document cannot read two ways in one response - rendered here and refused
    there - so the pass runs here too.
    """
    user = user or frappe.session.user
    if not has_doc_permission(doc, "read", user):
        return False

    return bool(has_user_permission(doc, user, ptype="read"))


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
