# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import sqlglot as sg


def extract_sql_table_refs(raw_sql: str, dialect: sg.Dialect | None = None) -> list[frappe._dict]:
    parsed = sg.parse_one(raw_sql, dialect=dialect)

    cte_aliases = {
        str(alias)
        for cte_exp in parsed.find_all(sg.exp.CTE)
        if (alias := getattr(cte_exp, "alias_or_name", None) or cte_exp.alias)
    }

    table_refs = []
    seen_refs = set()
    for table_exp in parsed.find_all(sg.exp.Table):
        table_name = table_exp.name
        if not table_name or table_name in cte_aliases:
            continue

        table_ref = frappe._dict(
            name=table_name,
            db=str(table_exp.db) if table_exp.db else None,
            catalog=str(table_exp.catalog) if table_exp.catalog else None,
        )
        ref_key = (table_ref.name, table_ref.db, table_ref.catalog)
        if ref_key in seen_refs:
            continue

        seen_refs.add(ref_key)
        table_refs.append(table_ref)

    return table_refs


def extract_query_deps_from_operations(operations: list) -> list[str]:
    """Extract all referenced query names from a list of operations."""
    return [
        op["table"]["query_name"]
        for op in operations
        if op.get("table")
        and op.get("table", {}).get("type") == "query"
        and op.get("table", {}).get("query_name")
    ]


def extract_table_deps_from_operations(operations: list) -> list[dict]:
    """Extract all unique (data_source, table_name) pairs from a list of operations."""
    seen: set[tuple] = set()
    result = []
    for op in operations:
        tbl = op.get("table") or {}
        if tbl.get("type") != "table":
            continue
        ds, tn = tbl.get("data_source"), tbl.get("table_name")
        if not ds or not tn:
            continue
        key = (ds, tn)
        if key in seen:
            continue
        seen.add(key)
        result.append({"data_source": ds, "table_name": tn})
    return result


def extract_table_deps_from_sql_operations(operations: list) -> list[dict]:
    """Extract unique (data_source, table_name) pairs from native SQL operations."""
    seen: set[tuple] = set()
    result = []
    for op in operations:
        if op.get("type") != "sql":
            continue
        raw_sql = op.get("raw_sql") or ""
        ds = op.get("data_source") or ""
        if not raw_sql or not ds:
            continue
        for ref in extract_sql_table_refs(raw_sql):
            key = (ds, ref.name)
            if key in seen:
                continue
            seen.add(key)
            result.append({"data_source": ds, "table_name": ref.name})
    return result


def sync_query_references(query_name: str, operations) -> None:
    """Rebuild edge rows for *query_name* in Insights Query Reference.

    Deletes all existing outgoing edges for this query then inserts fresh
    rows for every table and query reference found in operations.
    """
    from frappe.model.document import bulk_insert

    ops = frappe.parse_json(operations) or []
    frappe.db.delete("Insights Query Reference", {"query": query_name})

    docs = []

    all_table_deps = extract_table_deps_from_operations(ops) + extract_table_deps_from_sql_operations(ops)
    for tbl in all_table_deps:
        ref = frappe.new_doc("Insights Query Reference")
        ref.name = frappe.generate_hash(length=10)
        ref.query = query_name
        ref.ref_type = "Table"
        ref.data_source = tbl["data_source"]
        ref.table_name = tbl["table_name"]
        docs.append(ref)

    for dep_query in extract_query_deps_from_operations(ops):
        ref = frappe.new_doc("Insights Query Reference")
        ref.name = frappe.generate_hash(length=10)
        ref.query = query_name
        ref.ref_type = "Query"
        ref.ref_query = dep_query
        docs.append(ref)

    if docs:
        bulk_insert("Insights Query Reference", docs)


def get_direct_dependencies(query_name: str) -> list[str]:
    """Return the query names this query directly depends on, from the edge table."""
    return frappe.get_all(
        "Insights Query Reference",
        filters={"query": query_name, "ref_type": "Query"},
        pluck="ref_query",
    )


def transitive_closure(start: str) -> set[str]:
    """Return all query names reachable from start (not including start itself)."""
    reachable: set[str] = set()
    stack = list(get_direct_dependencies(start))
    while stack:
        node = stack.pop()
        if node in reachable:
            continue
        reachable.add(node)
        stack.extend(get_direct_dependencies(node))
    return reachable


def find_cycle(start: str, new_direct_deps: list[str]) -> list[str] | None:
    """
    Check whether declaring `new_direct_deps` as the direct dependencies of `start`
    would form a cycle. Returns the cycle path (e.g. ["A", "B", "A"]) or None.

    Used during validate() to catch cycles before they are persisted.
    """
    for dep in new_direct_deps:
        path = _find_path(dep, target=start, path=[start, dep], visited=set())
        if path is not None:
            return path
    return None


def _find_path(current: str, target: str, path: list[str], visited: set[str]) -> list[str] | None:
    if current == target:
        return path
    if current in visited:
        return None
    visited.add(current)
    for dep in get_direct_dependencies(current):
        result = _find_path(dep, target, [*path, dep], visited)
        if result is not None:
            return result
    return None
