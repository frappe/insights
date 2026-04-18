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


def get_direct_dependencies(query_name: str) -> list[str]:
    """Return the list of query names this query directly depends on, from the DB."""
    linked_queries = frappe.db.get_value("Insights Query v3", query_name, "linked_queries")
    return frappe.parse_json(linked_queries) or []


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
