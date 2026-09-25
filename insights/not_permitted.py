# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""A chart the reader may view but whose data they may not read.

The chart reads a site-DB table or a permlevel column that the reader's Frappe
permissions do not cover. It does not run. Its card stays in place and names
the doctypes it needs. This follows frappe's own query rule: one unreadable
table fails the whole `get_list`. The alternative is a card that says "No
data", which a reader takes for zero. See
`docs/adr/a-reader-never-sees-a-false-empty.md`.

The reader was already admitted to the chart, so naming the doctypes it needs
reveals nothing. **Not Found** is the answer for the content itself.
"""

from functools import wraps

import frappe

from insights.permission_user import permission_user, permission_user_for

# The columns this request's builds held back, each with its doctype. A chart
# that never reads such a column keeps running. The refusal comes only when a
# query names the column.
HELD_BACK = "insights_columns_held_back"


class NotPermitted(frappe.PermissionError):
    """Carries the doctypes the reader would need read on."""

    def __init__(self, message, doctypes: list[str] | None = None):
        super().__init__(message)
        self.doctypes = doctypes or []


def refuse(doctypes: list[str] | None = None, message: str | None = None) -> None:
    """Refuse a read and name the doctypes it needs. The only place the app raises `NotPermitted`.

    It throws through `frappe.throw`, so the message reaches the message log. A
    response carries the exception's own text only where tracebacks are
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

    A reader is admitted to a dashboard as soon as one card on it is readable.
    So every endpoint behind that dashboard can meet a table the reader may not
    read: a filter's value picker, a card's range, a table preview. There a
    refusal is an answer, not a failure. The reader was admitted, they cannot
    fix anything, and a retry cannot succeed. When each endpoint handled this
    itself, only one in eleven did.

    `empty` builds the endpoint's answer when it has nothing: a list for a
    picker, `None` for a range, the rendering keys for a card. A dict answer
    also carries `not_permitted` with the doctypes the reader would need. So a
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


def unreadable_doctypes(table_name: str, user: str | None = None) -> list[str]:
    """The doctypes `user` would need read on to read `table_name`. Empty if none.

    A child table has no permissions of its own. It needs read on one of its
    parents, so every parent is named, and any one of them is enough.
    """
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_parents

    doctype = table_name.removeprefix("tab")
    if not frappe.get_meta(doctype).istable:
        return [] if frappe.has_permission(doctype, "read", user=user) else [doctype]

    parents = get_parents(doctype)
    if any(frappe.has_permission(parent, "read", user=user) for parent in parents):
        return []
    return sorted(parents) or [doctype]


def has_permitted_chart(dashboard: str, user: str | None = None) -> bool:
    """Whether any chart on `dashboard` would run for `user`.

    A dashboard is Not Found when every chart on it is Not Permitted, or when
    `user` may not read any of them. Nothing on it is for this reader, and Not
    Found is the one answer for content a reader may not read. A partly
    permitted dashboard opens with its Not Permitted cards in place, so the
    layout never shifts. A chart is readable when `may_read` says so, the same
    check `view.charts_on` makes on the same cells.

    Nothing runs. A chart's tables come from the operations of its query and of
    every query that query sources. They come from the query's own row, not
    from the `Insights Query Reference` table, because a background job
    rebuilds that table after the save commits. Each chart is checked as the
    user it would run as, and `permission_user_for` decides that user: the
    owner while Run as owner is on, the key's user during a preview render, the
    reader otherwise.

    A table is readable when `check_table_permission` says so, the same rule
    the engine reads rows by: desk or a team grant on the site database, a team
    grant elsewhere.

    A dashboard with no charts is permitted, because nothing on it was refused.
    So is one whose charts were all deleted, and one with a chart that names no
    query. That is a normal saved state, and the card asks its author to
    configure it.
    """
    from insights.insights.doctype.insights_team.insights_team import check_table_permission
    from insights.insights.query_utils import table_references, transitive_closure
    from insights.resolver import may_read

    charts = frappe.get_all(
        "Insights Dashboard Chart v3",
        filters={"parent": dashboard, "parenttype": "Insights Dashboard v3"},
        pluck="chart",
    )
    if not charts:
        return True

    reader = user or frappe.session.user
    answered: dict[tuple[str, str], bool] = {}

    def readable(data_source: str, table_name: str, as_user: str) -> bool:
        key = (f"{data_source}.{table_name}", as_user)
        if key not in answered:
            answered[key] = check_table_permission(data_source, table_name, user=as_user, raise_error=False)
        return answered[key]

    rows = frappe.get_all("Insights Chart v3", filters={"name": ("in", charts)}, fields=["name", "query"])
    if not rows:
        return True
    for chart in rows:
        if not may_read(frappe.get_cached_doc("Insights Chart v3", chart.name), reader):
            continue
        if not chart.query:
            # nothing to refuse: the card asks this reader, as it asks the
            # author, to pick a chart type and configure it
            return True
        with permission_user(reader):
            as_user = permission_user_for(frappe._dict(doctype="Insights Chart v3", name=chart.name))
        queries = {chart.query, *transitive_closure(chart.query)}
        operations = frappe.get_all(
            "Insights Query v3", filters={"name": ("in", list(queries))}, pluck="operations"
        )
        if all(
            readable(ref["data_source"], ref["table_name"], as_user)
            for pipeline in operations
            for ref in table_references(pipeline)
        ):
            return True

    return False


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
