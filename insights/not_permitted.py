# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""A chart the reader may view but whose data they may not read.

It reads a site-DB table or a permlevel column their Frappe permissions do not
cover. It does not run, and its card stays in place naming the doctypes it
needs. This is frappe's own query rule — one unreadable table fails the whole
`get_list` — and the alternative is the card reading "No data", which a reader
takes for zero. See `docs/adr/a-reader-never-sees-a-false-empty.md`.

The reader was already admitted to the chart, so saying which doctypes it needs
reveals nothing. **Not Found** is the answer for the content itself.
"""

from functools import wraps

import frappe

from insights.permission_user import permission_user, permission_user_for

# the columns this request's builds held back, and the doctype each one
# belongs to. Holding back is what keeps a chart that never reads the column
# running, so the refusal waits until the query asks for it by name.
HELD_BACK = "insights_columns_held_back"


class NotPermitted(frappe.PermissionError):
    """Carries the doctypes the reader would need read on."""

    def __init__(self, message, doctypes: list[str] | None = None):
        super().__init__(message)
        self.doctypes = doctypes or []


def refuse(doctypes: list[str] | None = None, message: str | None = None) -> None:
    """Refuse a read, naming the doctypes it needs. The one way the app raises `NotPermitted`.

    Thrown the way `frappe.throw` throws, so the sentence reaches the message
    log: a response carries the exception's own text only where tracebacks are
    allowed, and without it the reader is told an endpoint's URL.
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
    """Take a refusal's sentence back out of the message log, once a surface draws it."""
    exc_id = getattr(refusal, "__frappe_exc_id", None)
    frappe.local.message_log = [
        message for message in frappe.local.message_log if message.get("__frappe_exc_id") != exc_id
    ]


def answers_refusal(empty):
    """Turn a refusal into the answer the surface draws. One statement, at the boundary.

    A reader is admitted to a dashboard as soon as one card on it is readable,
    so every endpoint behind that dashboard can meet a table this reader may not
    read - a filter's value picker, a card's range, a table preview. A refusal
    there is an answer and not a failure: the reader was admitted, they own
    nothing they could fix, and a retry cannot succeed. Left to each endpoint it
    was remembered once in eleven.

    `empty` builds what the endpoint answers with when it has nothing - a list
    for a picker, `None` for a range, the rendering keys for a card. A mapping
    also carries `not_permitted`, naming the doctypes the reader would need, so a
    card can say why it is blank instead of reading as zero.

    An endpoint belongs here once something draws what it answers with. Where
    the surface reads that answer as success it draws a false empty, which is
    the defect this exists to remove - so a count, whose empty answer *is* a
    zero and carries nothing for the marker to ride on, keeps raising, and so
    does a run whose editor already draws the failure it comes back with.

    A download is not one of these either. It is an act rather than a picture, so
    it keeps the refusal, whose message already names what is missing.

    Every refusal it catches is a `NotPermitted`, which is why nothing in the
    app refuses a read with a bare `frappe.PermissionError`: `NotPermitted`
    subclasses that, so widening the catch would swallow the refusals that must
    stay hard - a forged declaration, a query reference nobody may read.
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

    A child table has no permissions of its own, so what it needs is read on one
    of its parents, and every parent is named: holding any one of them is enough.
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

    A dashboard every chart of which is Not Permitted, or that `user` may not
    read at all, reads as Not Found: there is nothing on it for this reader,
    and Not Found is the one answer for content a reader may not read. A partly
    permitted one opens with its Not Permitted cards in place, so the layout
    never shifts. A chart is read as `may_read` answers it, the question
    `view.charts_on` asks of the same cells.

    Answered without running anything. A chart's tables are read off the
    operations of the query behind it and of every query that one sources —
    the query's own row, not the `Insights Query Reference` edge table, which a
    background job rebuilds after the save commits. Each chart is asked under
    the user it would run as, and `permission_user_for` is the one place that
    answers that: the owner while the chart's Check is on, the key's user
    under a preview render, the reader otherwise.

    A table is read as `check_table_permission` answers it, the rule the
    engine reads rows by: on site data desk or a team grant, elsewhere a team
    grant.

    A dashboard with no charts is permitted: nothing on it was refused. So is
    one whose charts have all been deleted, and a chart that names no query - a
    normal saved state, whose card asks its own author to configure it.
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
            # nothing to refuse: the card says "pick a chart type and configure
            # options", to this reader as to the author who dragged it on
            return True
        # the user the chart would run as, from the one place that answers it:
        # its owner while its Check is on, the key's user under a preview
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
    """Drop what the last build held back, so one build never answers for another."""
    setattr(frappe.local, HELD_BACK, {})


def held_back_columns() -> set[str]:
    """The names this request's builds held back.

    What a reader may not read must not change the shape of a result, only its
    contents. A join names its output by comparing the two sides' column sets,
    and those sets are already narrowed by the time it looks - so it puts these
    back first. See `IbisQueryBuilder.rename_duplicate_columns`.
    """
    return set(getattr(frappe.local, HELD_BACK, None) or {})


def held_back_doctype(column_name: str) -> str | None:
    """The doctype a column this build held back was read on.

    A column the reader may not read is held back from the table rather than
    refused there, because a chart that never names it is none of its business.
    So the query asking for it by name is where the answer is given - and every
    caller that names it is answered, whether the answer is a refusal or a
    column that is not there.
    """
    held = getattr(frappe.local, HELD_BACK, None) or {}
    if column_name in held:
        return held[column_name]
    # SQL names a column in any case, and the database reads it so
    folded = column_name.lower()
    return next((doctype for key, doctype in held.items() if key.lower() == folded), None)
