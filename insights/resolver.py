# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Turns a content reference into a site-local document name.

A reference is what a consumer app, a desk route or a bookmark carries. Three
forms are accepted for a dashboard, two for a chart:

    docname      the hash primary key, site-local
    route        the cosmetic, human-readable dashboard key
    v2 name      the primary key this document carried before the rename to v3,
                 kept in `old_name` so a link shared back then still opens

The lookups run in order: docname first, then route, then the v2 name. A route
that equals another dashboard's hash name resolves to that dashboard. The
internal key wins, and nothing internal references a route.
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

    Raises `frappe.DoesNotExistError` when the reference resolves to nothing or
    to a document the current user cannot read. Both cases raise the same error
    on purpose, so a read endpoint built on this cannot probe what exists on the
    site.

    A dashboard is also Not Found when every chart on it is Not Permitted or
    unreadable. `has_permitted_chart` checks that without running any chart. It
    is part of the read check, so it belongs here. A user who may write the
    dashboard opens it whatever its charts return, because they can fix it.
    """
    name = resolve(doctype, reference)
    if not name or not may_read(frappe.get_doc(doctype, name)):
        not_found()

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
    """Whether this reader may read this content. The one place that decides it.

    Frappe checks access in two stacks, and they can differ. The grants come
    from the Insights controller. They are checked here directly, because
    frappe's role check would need every reader, Guest included, to have read
    on the doctype. That would also open `/api/resource` to them.

    The role check also applies User Permissions, and the controller does not.
    A User Permission on `Insights Dashboard v3`, or on its workbook, narrows
    `get_doc`, the list query and `can_write`. One response must not render a
    document in one place and refuse it in another, so User Permissions are
    applied here too.
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
    # last, because a v2 name is history: a document's current name must win
    # over another document's old name
    return frappe.db.get_value(doctype, {"old_name": reference}, "name", order_by="creation asc")
