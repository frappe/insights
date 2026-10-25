# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""A chart the reader may view but whose data they may not read.

The chart reads a site-DB table or a permlevel column that the reader's Frappe
permissions do not cover. It does not run. Its card stays in place and names
the doctypes it needs. This follows frappe's own query rule: one unreadable
table fails the whole `get_list`. The alternative is a card that says "No
data", which a reader takes for zero. See
`docs/adr/a-reader-never-sees-a-false-empty.md`.

The reader was already allowed on the chart, so naming the doctypes it needs
reveals nothing. Content the reader may not read is refused without them
(`resolver.no_access`).
"""

from functools import wraps

import frappe

from insights.permission_user import permission_user, permission_user_for

# The columns this request's builds held back, each with its doctype. A chart
# that never reads such a column keeps running. The refusal comes only when a
# query names the column.
HELD_BACK = "insights_columns_held_back"


class NotPermitted(frappe.PermissionError):
    """Holds the doctypes the reader would need read on."""

    def __init__(self, message, doctypes: list[str] | None = None):
        super().__init__(message)
        self.doctypes = doctypes or []


def refuse(doctypes: list[str] | None = None, message: str | None = None) -> None:
    """Refuse a read and name the doctypes it needs. The only place the app raises `NotPermitted`.

    It throws through `frappe.throw`, so the message reaches the message log. A
    response includes the exception's own text only where tracebacks are
    allowed. Without the message log, the reader would see only an endpoint's URL.
    """
    doctypes = doctypes or []
    if not message:
        named = ", ".join(frappe.bold(doctype) for doctype in doctypes)
        message = (
            frappe._("Needs read access to {0}").format(named)
            if doctypes
            else frappe._("You do not have access to the data behind this chart")
        )
    frappe.throw(message, exc=NotPermitted(message, doctypes))


def forget_refusal(refusal: NotPermitted) -> None:
    """Remove a refusal's message from the message log once the caller shows the refusal itself."""
    exc_id = getattr(refusal, "__frappe_exc_id", None)
    frappe.local.message_log = [
        message for message in frappe.local.message_log if message.get("__frappe_exc_id") != exc_id
    ]


def answers_refusal(empty):
    """Turn a refusal into the answer the UI renders. Apply it once, on the endpoint.

    A reader is allowed on a dashboard as soon as one card on it is readable.
    So every endpoint behind that dashboard can meet a table the reader may not
    read: a filter's value picker, a card's range, a table preview. There a
    refusal is an answer, not a failure. The reader was allowed in, they cannot
    fix anything, and a retry cannot succeed. When each endpoint handled this
    itself, only one in eleven did.

    `empty` builds the endpoint's answer when it has nothing: a list for a
    picker, `None` for a range, the rendering keys for a card. A dict answer
    also includes `not_permitted` with the doctypes the reader would need. So a
    card can say why it is blank instead of reading as zero.

    Use it on an endpoint only when the UI renders its answer. If the UI reads
    that answer as success, it shows a false empty, which is the defect this
    removes. So a count keeps raising, because its empty answer is a zero and
    has no place for the marker. A query run keeps raising too, because its
    editor already shows the failure.

    A download also keeps the refusal. It is an action, not a display, and its
    message already names what is missing.

    It catches only `NotPermitted`, so every read refusal in the app raises
    `NotPermitted`, never a bare `frappe.PermissionError`. Catching
    `frappe.PermissionError`, its parent, would also swallow the refusals that
    must stay hard: a forged declaration, a query reference nobody may read.
    """

    def decorate(fn):
        @wraps(fn)
        def answer(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except NotPermitted as refusal:
                forget_refusal(refusal)
                nothing = empty()
                if isinstance(nothing, dict):
                    nothing["not_permitted"] = {"doctypes": refusal.doctypes}
                return nothing

        return answer

    return decorate


def unreadable_doctypes(table_name: str, user: str | None = None, reads=None) -> list[str]:
    """The doctypes `user` would need read on to read `table_name`. Empty if none.

    A child table has no permissions of its own. It needs read on one of its
    parents, so every parent is named, and any one of them is enough.

    `reads` answers whether a doctype is readable in place of desk's check for
    `user`, as `role_reads` does for a role.
    """
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_parents

    reads = reads or (lambda doctype: frappe.has_permission(doctype, "read", user=user))
    doctype = table_name.removeprefix("tab")
    if not frappe.get_meta(doctype).istable:
        return [] if reads(doctype) else [doctype]

    parents = get_parents(doctype)
    if any(reads(parent) for parent in parents):
        return []
    return sorted(parents) or [doctype]


# the roles desk gives every signed-in desk user besides their own
ROLES_EVERY_DESK_USER_HOLDS = ("All", "Guest", "Desk User")


def role_reads(role: str):
    """Whether a desk user who holds only `role` may read a doctype: whether a
    role permission at level 0 gives `role`, or a role every desk user holds,
    read on it. Rows a User Permission narrows still leave the doctype readable.
    A column above level 0 is not checked, so its chart can still say Not
    Permitted."""
    held = {role, *ROLES_EVERY_DESK_USER_HOLDS}
    return lambda doctype: any(
        perm.read and perm.role in held and not perm.permlevel
        for perm in frappe.get_meta(doctype).permissions
    )


def roles_without_read(dashboard: str, roles: list[str]) -> dict[str, list[str]]:
    """The doctypes each of `roles` would need read on for every chart on
    `dashboard` to run for a reader who holds only that role. A role that
    reads them all is left out.

    A chart that runs as its owner needs nothing of its reader, as
    `permission_user_for` decides. Off the site database a role grants nothing
    on its own, and a team may still grant its holders a table, so only desk's
    doctypes are named.
    """
    from insights.permission_user import declared_owner

    charts = frappe.get_all(
        "Insights Dashboard Chart v3",
        filters={"parent": dashboard, "parenttype": "Insights Dashboard v3"},
        pluck="chart",
    )
    tables = set()
    for chart in frappe.get_all(
        "Insights Chart v3", filters={"name": ("in", charts or [""])}, fields=["name", "query"]
    ):
        if chart.query and not declared_owner(frappe._dict(doctype="Insights Chart v3", name=chart.name)):
            tables |= query_tables(chart.query)

    needed = {}
    for role in roles:
        reads = role_reads(role)
        if doctypes := sorted(
            {doctype for table in tables for doctype in site_table_doctypes(*table, reads=reads)}
        ):
            needed[role] = doctypes
    return needed


def site_table_doctypes(data_source: str, table_name: str, user: str | None = None, reads=None) -> list[str]:
    """The doctypes `user` would need read on to read a table. Empty off the
    site database, where no doctype grants a table, and for a table that has
    no doctype. `reads` is as for `unreadable_doctypes`."""
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
        is_site_db,
        strip_schema_prefix,
    )

    table = strip_schema_prefix(table_name)
    if not is_site_db(data_source) or table == "tabSingles":
        return []
    try:
        return unreadable_doctypes(table, user, reads)
    except frappe.DoesNotExistError:
        return []  # nosemgrep - a table without a doctype names no doctype to grant


def query_tables(query: str) -> set[tuple[str, str]]:
    """The `(data_source, table_name)` of every table `query` reads, its sources' included."""
    from insights.insights.query_utils import table_references, transitive_closure

    operations = frappe.get_all(
        "Insights Query v3", filters={"name": ("in", [query, *transitive_closure(query)])}, pluck="operations"
    )
    return {
        (ref["data_source"], ref["table_name"])
        for pipeline in operations
        for ref in table_references(pipeline)
    }


def query_refusal(query: str, user: str) -> list[str] | None:
    """None when `user` may read every table `query` reads. Otherwise the
    doctypes they would need read on, which is empty off the site database.

    Every table is checked, not only up to the first refusal, so the answer
    names everything the query needs.
    """
    from insights.insights.doctype.insights_team.insights_team import check_table_permission

    refused = [
        table
        for table in query_tables(query)
        if not check_table_permission(*table, user=user, raise_error=False)
    ]
    if not refused:
        return None
    return sorted({doctype for table in refused for doctype in site_table_doctypes(*table, user)})


def refused_doctypes(dashboard: str, user: str | None = None) -> list[str] | None:
    """None when a chart on `dashboard` would run for `user`. Otherwise the
    doctypes they would need read on, which is empty when they may read none
    of its charts.

    A dashboard on which no chart would run is refused: nothing on it is for
    this reader. A partly permitted dashboard opens with its Not Permitted
    cards in place, so the layout never shifts. A chart is readable when
    `may_read` says so, the same check `view.charts_on` makes on the same cells.

    Nothing runs. A chart's tables come from the operations of its query and of
    every query that query sources. They come from the query's own row, the
    source the `Insights Query Reference` table is derived from. Each chart is
    checked as the user it would run as, and `permission_user_for` decides that
    user: the owner while Run as owner is on, the key's user during a preview
    render, the reader otherwise.

    A table is readable when `check_table_permission` says so, the same rule
    the engine reads rows by: desk on the site database, a team grant
    elsewhere.

    A dashboard with no charts is permitted, because nothing on it was refused.
    So is one whose charts were all deleted, and one with a chart that names no
    query. That is a normal saved state, and the card asks its author to
    configure it.
    """
    from insights.resolver import may_read

    charts = frappe.get_all(
        "Insights Dashboard Chart v3",
        filters={"parent": dashboard, "parenttype": "Insights Dashboard v3"},
        pluck="chart",
    )
    if not charts:
        return None

    reader = user or frappe.session.user
    needed: set[str] = set()
    rows = frappe.get_all("Insights Chart v3", filters={"name": ("in", charts)}, fields=["name", "query"])
    if not rows:
        return None
    for chart in rows:
        if not may_read(frappe.get_cached_doc("Insights Chart v3", chart.name), reader):
            continue
        if not chart.query:
            # nothing to refuse: the card asks this reader, as it asks the
            # author, to pick a chart type and configure it
            return None
        with permission_user(reader):
            as_user = permission_user_for(frappe._dict(doctype="Insights Chart v3", name=chart.name))
        refusal = query_refusal(chart.query, as_user)
        if refusal is None:
            return None
        needed.update(refusal)

    return sorted(needed)


def hold_back(columns: dict[str, str]) -> None:
    """Record columns a projection held back, keyed by column name."""
    if not columns:
        return
    held = getattr(frappe.local, HELD_BACK, None)
    if held is None:
        held = {}
        setattr(frappe.local, HELD_BACK, held)
    held.update(columns)


def forget_held_back() -> None:
    """Clear what the last build held back, so one build never reports another's columns."""
    setattr(frappe.local, HELD_BACK, {})


def held_back_columns() -> set[str]:
    """The column names this request's builds held back.

    A column the reader may not read must change a result's contents, not its
    shape. A join names its output columns by comparing the column sets of its
    two sides. Those sets are already narrowed when it compares them, so it
    adds these back first. See `IbisQueryBuilder.rename_duplicate_columns`.
    """
    return set(getattr(frappe.local, HELD_BACK, None) or {})


def held_back_doctype(column_name: str) -> str | None:
    """The doctype of a column this build held back.

    A column the reader may not read is held back from the table, not refused
    there, so a chart that never names it still runs. The query that names it
    gets the answer, and so does every other caller that names it. The answer
    is a refusal or a missing column.
    """
    held = getattr(frappe.local, HELD_BACK, None) or {}
    if column_name in held:
        return held[column_name]
    # SQL column names are case-insensitive
    folded = column_name.lower()
    return next((doctype for key, doctype in held.items() if key.lower() == folded), None)
