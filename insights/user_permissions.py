# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The User Permissions that narrowed the rows an execution returned.

A narrowed number looks like the total. A Sales User limited to Territory North
sees "Revenue" and takes it for the company's. So the card says which
permissions narrowed it. See `docs/adr/a-reader-never-sees-a-false-empty.md`.

Only a real User Permission record is named. A role's match condition also
narrows the rows, but it names no document, so there is nothing to show.
Insights' own narrowing names nothing either, so the card says only that the
reader's permissions narrowed it. That covers two cases: a team's Table
Restriction that removes rows the reader reads, and a column that the per-cell
rule blanks on rows only desk admits, when the execution reads that column.
Desk's own row narrowing never sets this mark. Neither does a grant that only
adds rows to what desk allows.

Every entry records the user it applied to, because an execution does not
always run as the reader. A Public chart runs as its owner, and an alert as the
user who enabled it. Their User Permissions name documents (a customer, a
company, a territory) that the reader was never shown, and they are not the
reader's restriction. So the record is read back for one user, and an
execution that ran as another user reports nothing to this one.

Recorded where the row filter is built, because only that code knows what
frappe applied. Read back after the query runs.
"""

import frappe
import ibis.expr.operations as ops
from frappe.model.db_query import requires_owner_constraint

APPLIED = "insights_applied_user_permissions"
# the users a team's Table Restriction or the per-cell rule narrowed this build for
NARROWED = "insights_narrowed_by_permissions"
# the relations the per-cell rule blanked columns on, and for whom
BLANKED = "insights_blanked_by_permissions"


def forget() -> None:
    """Clear the last build's records, so one build never reports for another."""
    setattr(frappe.local, APPLIED, {})
    setattr(frappe.local, NARROWED, set())
    setattr(frappe.local, BLANKED, [])


def record_blanked(user: str, relation: ops.Relation, columns: list[str]) -> None:
    """Record that `relation` blanks `columns` on some rows for `user`.

    The relation keeps these columns whether or not the query uses them. So
    whether this narrowed anything is known only from the whole query; see
    `record_blanked_reads`.
    """
    blanked = getattr(frappe.local, BLANKED, None)
    if blanked is None:
        blanked = []
        setattr(frappe.local, BLANKED, blanked)
    blanked.append((user, relation, set(columns)))


def record_blanked_reads(query) -> None:
    """Record a narrowing for each blanked column that `query` reads."""
    for user, relation, columns in getattr(frappe.local, BLANKED, None) or []:
        if reads_columns(query.op(), relation, columns):
            record_narrowed(user)


def reads_columns(root: ops.Relation, relation: ops.Relation, columns: set[str]) -> bool:
    """Whether the rows of `root` read one of `columns` of `relation`.

    Walks down from `root`, tracking which columns each relation is read for.
    A projection passes on only the columns its outputs are computed from. So a
    column no later step reads is not read, even though the relation still has
    it. An unknown relation is read for all its columns.
    """
    needed: dict[ops.Relation, set[str]] = {}
    pending = [(root, set(root.schema.names))]
    while pending:
        node, names = pending.pop()
        first = node not in needed
        new = names - needed.get(node, set())
        if not first and not new:
            continue
        needed.setdefault(node, set()).update(new)
        if node == relation and new & columns:
            return True
        pending.extend(_read_from(node, new, first))
    return False


def _read_from(node: ops.Relation, names: set[str], first: bool) -> list[tuple[ops.Relation, set[str]]]:
    """The relations `node` reads, and for which columns, when asked for `names`.
    The parts that decide which rows it has are read on the `first` visit only."""
    values: list = []
    passed: list[tuple[ops.Relation, set[str]]] = []

    if isinstance(node, ops.Project | ops.JoinChain):
        values = [node.values[name] for name in names if name in node.values]
        if isinstance(node, ops.JoinChain) and first:
            values += [predicate for link in node.rest for predicate in link.predicates]
    elif isinstance(node, ops.Aggregate):
        values = [node.metrics[name] for name in names if name in node.metrics]
        if first:
            values += list(node.groups.values())
    elif isinstance(node, ops.Filter | ops.Sort | ops.Limit | ops.DropColumns | ops.FillNull | ops.Reference):
        passed = [(node.parent, names)]
        if first and isinstance(node, ops.Filter):
            values = list(node.predicates)
        if first and isinstance(node, ops.Sort):
            values = list(node.keys)
    elif isinstance(node, ops.Set) and not node.distinct:
        passed = [(node.left, names), (node.right, names)]
    else:
        # a distinct, sampled or raw SQL relation, or any other: it reads every
        # column of its inputs
        passed = [
            (child, set(child.schema.names)) for child in node.__children__ if isinstance(child, ops.Relation)
        ]
        values = [child for child in node.__children__ if isinstance(child, ops.Value)]

    return passed + [read for value in values for read in _fields_of(value)]


def _fields_of(value: ops.Node) -> list[tuple[ops.Relation, set[str]]]:
    """The relation columns `value` is computed from. A subquery reads its whole relation."""
    reads = []
    pending, seen = [value], set()
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        if isinstance(node, ops.Field):
            reads.append((node.rel, {node.name}))
        elif isinstance(node, ops.Relation):
            reads.append((node, set(node.schema.names)))
        else:
            pending.extend(child for child in node.__children__ if isinstance(child, ops.Node))
    return reads


def record_narrowed(user: str) -> None:
    """Record that a restriction narrowed the rows or cells this build returned for `user`."""
    narrowed_for = getattr(frappe.local, NARROWED, None)
    if narrowed_for is None:
        narrowed_for = set()
        setattr(frappe.local, NARROWED, narrowed_for)
    narrowed_for.add(user)


def record(user: str, match_filters: dict[str, list[str]]) -> None:
    """Merge one of frappe's `DatabaseQuery.match_filters` entries, for the user
    the build applied it to."""
    applied_for = getattr(frappe.local, APPLIED, None)
    if applied_for is None:
        applied_for = {}
        setattr(frappe.local, APPLIED, applied_for)
    for doctype, documents in (match_filters or {}).items():
        applied_for.setdefault(user, {}).setdefault(doctype, set()).update(documents)


def narrowing(doctype: str, user: str, parent_doctype: str | None = None) -> dict[str, list[str]]:
    """The User Permissions frappe applies to a list of `doctype` for `user`.

    Frappe records this as `DatabaseQuery.match_filters`, but only its legacy
    query implementation sets it, and `frappe.get_list` no longer uses that
    one. This reads the same answer from the public `get_user_permissions`, so
    every chart's row filter stays on `get_list`. The supported path should
    report what it applied; that is a change for frappe.

    It reads the doctype frappe checks, the way frappe reads it: every Link
    field of that doctype, plus the doctype itself as `name`, minus the fields
    that opt out. Frappe checks a child table against its parent
    (`permission_doctype = parent_doctype or doctype`) and ignores the child's
    own links. So a User Permission on a field only the parent links narrows
    the rows, and one on a field only the child links narrows nothing.
    """
    permission_doctype = parent_doctype or doctype

    held = frappe.permissions.get_user_permissions(user)
    if not held:
        return {}

    # frappe skips User Permissions in these two cases and narrows by owner or
    # by shares instead. Naming them would blame the reader's restriction for
    # a narrowing it did not cause
    role_permissions = frappe.permissions.get_role_permissions(permission_doctype, user=user)
    if not (role_permissions.get("read") or role_permissions.get("select")):
        return {}
    if requires_owner_constraint(role_permissions):
        return {}

    meta = frappe.get_meta(permission_doctype)
    links = [*meta.get_link_fields(), frappe._dict(options=permission_doctype, fieldname="name")]

    narrowed: dict[str, list[str]] = {}
    for field in links:
        if field.get("ignore_user_permissions"):
            continue

        # a User Permission applies only to the doctype in its `applicable_for`,
        # or to every doctype when that is empty
        documents = [
            permission["doc"]
            for permission in held.get(field.get("options")) or []
            if permission.get("applicable_for") in (None, "", permission_doctype)
        ]
        if documents:
            narrowed[field.get("options")] = documents

    return narrowed


def scope(user: str) -> dict:
    """What narrowed this execution for `user`, in the shape a card's answer carries.

    `user_permissions` has one entry per doctype, in a stable order.
    `narrowed_by_permissions` marks a narrowing with nothing to name. Empty
    when nothing narrowed it, so the card shows no scope.
    """
    recorded = (getattr(frappe.local, APPLIED, None) or {}).get(user) or {}
    answer = {}
    if recorded:
        answer["user_permissions"] = [
            {"doctype": doctype, "documents": sorted(recorded[doctype])} for doctype in sorted(recorded)
        ]
    if user in (getattr(frappe.local, NARROWED, None) or set()):
        answer["narrowed_by_permissions"] = True
    return answer
