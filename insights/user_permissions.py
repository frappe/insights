# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The User Permissions that narrowed the rows an execution returned.

A scoped number reads as the whole one — a Sales User restricted to Territory
North sees "Revenue" and takes it for the company's. So the card says which
access narrowed it. See `docs/adr/a-reader-never-sees-a-false-empty.md`.

Only a real User Permission record is named. A role's match condition narrows
the rows too, but it is not a grant anybody holds a document for, and there is
nothing to name. Insights' own narrowing names nothing either, so the card says
only that the reader's permissions narrowed it: a team's Table Restriction that
cuts the rows the reader reads, and a column the per-cell rule blanks on the rows
only desk admits, when the execution reads that column. Desk's own row narrowing
never marks, and neither does a grant that only adds rows to desk's.

Every entry carries the user it was applied to, because an execution does not
always run as the reader: a Public chart runs as its owner, an alert as the user
it was enabled by. Those grants name documents — a customer, a company, a
territory — that the reader was never published, and they are not a restriction
the reader holds. So the mark is read back for one user, and an execution that
ran as somebody else has nothing to say to this one.

Recorded where the row filter is built, because that is the only place that
knows what frappe applied, and read back after the query has run.
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
    """Drop what the last build applied, so one build never answers for another."""
    setattr(frappe.local, APPLIED, {})
    setattr(frappe.local, NARROWED, set())
    setattr(frappe.local, BLANKED, [])


def record_blanked(user: str, relation: ops.Relation, columns: list[str]) -> None:
    """Record that `relation` blanks `columns` on some rows for `user`.

    A table carries every column it is read with, so whether this narrowed
    anything is known only once the execution is: `record_blanked_reads`.
    """
    blanked = getattr(frappe.local, BLANKED, None)
    if blanked is None:
        blanked = []
        setattr(frappe.local, BLANKED, blanked)
    blanked.append((user, relation, set(columns)))


def record_blanked_reads(query) -> None:
    """Record the narrowing of each blanked column the execution of `query` reads."""
    for user, relation, columns in getattr(frappe.local, BLANKED, None) or []:
        if reads_columns(query.op(), relation, columns):
            record_narrowed(user)


def reads_columns(root: ops.Relation, relation: ops.Relation, columns: set[str]) -> bool:
    """Whether the rows of `root` read one of `columns` of `relation`.

    Walked down from `root`, carrying the columns each relation is read for: a
    projection hands on only what the columns asked of it are made of, so a
    column no later step reads is not read, though the relation still carries
    it. A relation this does not know is read for every column it has.
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
    What decides which rows it has is asked on the `first` visit only."""
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
        # a distinct, a sampled or a raw SQL relation, and any other: it reads
        # every column of what it is built on
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
    """Record that a grant's restriction narrowed the rows or cells this build gave `user`."""
    narrowed_for = getattr(frappe.local, NARROWED, None)
    if narrowed_for is None:
        narrowed_for = set()
        setattr(frappe.local, NARROWED, narrowed_for)
    narrowed_for.add(user)


def record(user: str, match_filters: dict[str, list[str]]) -> None:
    """Take one of frappe's own `DatabaseQuery.match_filters` entries, for the
    user the build applied it to."""
    applied_for = getattr(frappe.local, APPLIED, None)
    if applied_for is None:
        applied_for = {}
        setattr(frappe.local, APPLIED, applied_for)
    for doctype, documents in (match_filters or {}).items():
        applied_for.setdefault(user, {}).setdefault(doctype, set()).update(documents)


def narrowing(doctype: str, user: str, parent_doctype: str | None = None) -> dict[str, list[str]]:
    """The User Permissions frappe applies to a list of `doctype` for `user`.

    Frappe records this itself, as `DatabaseQuery.match_filters`, but only the
    legacy query implementation exposes it and `frappe.get_list` no longer runs
    that one. Reading the same answer off the public `get_user_permissions`
    keeps the row filter every chart stands on with `get_list`: the supported
    path should report what it applied, and that is a change for frappe.

    Read about the doctype frappe decides on, and read the way it reads: every
    Link field of that doctype, plus the doctype itself under `name`, minus the
    fields that opt out. A child table is decided on by its parent - frappe sets
    `permission_doctype = parent_doctype or doctype` and never looks at the
    child's own links - so a grant on a field only the parent links narrows the
    rows, and one on a field only the child links narrows nothing.
    """
    permission_doctype = parent_doctype or doctype

    held = frappe.permissions.get_user_permissions(user)
    if not held:
        return {}

    # the two places frappe cuts the rows by something else and skips user
    # permissions entirely. Naming them anyway tells the reader a restriction
    # they hold narrowed a number that owner or sharing narrowed
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

        # a permission cut for one doctype narrows that doctype's own list
        documents = [
            permission["doc"]
            for permission in held.get(field.get("options")) or []
            if permission.get("applicable_for") in (None, "", permission_doctype)
        ]
        if documents:
            narrowed[field.get("options")] = documents

    return narrowed


def scope(user: str) -> dict:
    """What narrowed this execution for `user`, as a card's answer carries it.

    `user_permissions`, one entry per doctype in a stable order, and
    `narrowed_by_permissions` for a narrowing with nothing to name. Empty when
    nothing narrowed it, so a card that has no scope is the card it was.
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
