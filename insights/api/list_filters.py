"""Helpers shared by the workbook and dashboard lists."""

from collections.abc import Callable

import frappe
from frappe.query_builder.functions import Max

from insights.permissions import InsightsPermissions

DEFAULT_SOURCES = ("created", "shared")
NEGATED_OPERATORS = {"!=": "=", "not like": "like", "not in": "in"}

# (is_pattern, values) -> names of the listed documents that match, or None when
# the match answers no pattern
Match = Callable[[bool, list], list | None]


def get_source_filters(doctype: str, sources: list | None) -> list:
    """`get_list` filters keeping the documents from the chosen sources.

    sources: any of "created" (owned by the user), "shared" (given to the user by
    someone else) and "others" (neither; only an admin reads any). Created and
    shared split the user's grants and others is everything outside them, so a
    choice without others keeps a set of grants and a choice with it drops the
    grants left out.
    """
    sources = sources or DEFAULT_SOURCES
    user = frappe.session.user
    granted = set(InsightsPermissions(user).get_granted(doctype))
    created = set(frappe.get_all(doctype, filters={"owner": user}, pluck="name"))
    chosen = set()
    if "created" in sources:
        chosen |= created
    if "shared" in sources:
        chosen |= granted - created
    if "others" not in sources:
        return [["name", "in", list(chosen)]]
    dropped = granted - chosen
    return [["name", "not in", list(dropped)]] if dropped else []


def get_content_filters(filters: list, matches: dict[str, Match]) -> list:
    """Turn the list's filters into `get_list` filters.

    A declared filter becomes a `name in` or `name not in` over the documents its
    match returns. Any other filter names a column and passes through.
    """
    list_filters = []
    for fieldname, operator, value in filters:
        match = matches.get(fieldname)
        if not match:
            list_filters.append([fieldname, operator, value])
            continue

        operator = operator.lower()
        if operator == "is":
            operator, value = ("like" if value == "set" else "not like"), "%"
        negated = operator in NEGATED_OPERATORS
        operator = NEGATED_OPERATORS.get(operator, operator)
        values = value if operator == "in" else [value]
        names = match(operator == "like", values) if values else []
        if names is None:
            # no document meets a condition the match does not answer, negated or not
            list_filters.append(["name", "in", []])
            continue
        list_filters.append(["name", "not in" if negated else "in", names])
    return list_filters


def match_records(doctype: str, column: str) -> Match:
    """Match a picked record by name, or typed text against record titles.

    `column` is the record's column holding the listed document's name.
    """

    def match(is_pattern, values):
        alternatives = [[["title", "like", v]] for v in values] if is_pattern else [[["name", "in", values]]]
        return _readable(doctype, column, alternatives)

    return match


# How a query's `operations` JSON names each value. Matched with LIKE until the
# values get columns of their own.
OPERATIONS_KEYS = {
    "data_source": '"data_source": "{}"',
    "table_name": '"table_name": "{}"',
}


def match_operations(key: str, column: str) -> Match:
    """Match queries whose operations name a data source or table.

    A picked table is an Insights Table v3, which queries name by its data source
    and table. `column` is the query's column holding the listed document's name.
    """

    def match(is_pattern, values):
        return _readable(
            "Insights Query v3", column, [_operations_filters(key, v, is_pattern) for v in values]
        )

    return match


def _operations_filters(key: str, value: str, is_pattern: bool) -> list:
    def contains(k, v):
        return ["operations", "like", "%" + OPERATIONS_KEYS[k].format(v) + "%"]

    if is_pattern:
        return [contains(key, value)]
    if key == "table_name":
        table = frappe.db.get_value("Insights Table v3", value, ["data_source", "table"], as_dict=True)
        if not table:
            return [contains("table_name", _escape_like(value))]
        return [
            contains("data_source", _escape_like(table.data_source)),
            contains("table_name", _escape_like(table.table)),
        ]
    return [contains(key, _escape_like(value))]


def _readable(doctype: str, column: str, alternatives: list[list]) -> list:
    """`column` of the documents of `doctype` the caller may read that meet any of `alternatives`.

    Only what `frappe.get_list` returns: a match over documents the caller may
    not read tells them what those documents hold, one guess at a time.
    """
    matched = set()
    for filters in alternatives:
        matched.update(frappe.get_list(doctype, filters=filters, pluck=column, limit=0))
    return list(matched)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_shares(doctype: str, names: list) -> tuple[set, dict]:
    """The documents shared with everyone, and the users each is shared with."""
    if not names:
        return set(), {}

    rows = frappe.get_all(
        "DocShare",
        filters={"share_doctype": doctype, "share_name": ["in", names], "read": 1},
        fields=["share_name", "user", "everyone"],
    )
    org_shared = {row.share_name for row in rows if row.everyone}
    shared_users: dict[str, list] = {}
    for row in rows:
        if row.user:
            shared_users.setdefault(row.share_name, []).append(row.user)
    return org_shared, shared_users


def get_last_opened(doctype: str, names: list | None = None) -> dict[str, str]:
    """When the current user last opened each document, or each of `names`."""
    ViewLog = frappe.qb.DocType("View Log")
    query = (
        frappe.qb.from_(ViewLog)
        .select(ViewLog.reference_name, Max(ViewLog.creation))
        .where((ViewLog.reference_doctype == doctype) & (ViewLog.viewed_by == frappe.session.user))
        .groupby(ViewLog.reference_name)
    )
    if names is not None:
        query = query.where(ViewLog.reference_name.isin([str(name) for name in names] or [""]))
    return {str(name): opened for name, opened in query.run()}
