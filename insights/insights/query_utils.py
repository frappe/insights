# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import sqlglot as sg


def extract_sql_table_refs(raw_sql: str, dialect: sg.Dialect | None = None) -> list[frappe._dict]:
    try:
        parsed = sg.parse_one(raw_sql, dialect=dialect)
    except Exception:
        # If parsing fails, we return an empty list to avoid blocking the user from saving their query.
        # In the future, we may want to log these exceptions to help improve our SQL parsing capabilities.
        return []

    cte_aliases = {cte_exp.alias_or_name for cte_exp in parsed.find_all(sg.exp.CTE) if cte_exp.alias_or_name}

    table_refs = []
    seen_refs = set()
    for table_exp in parsed.find_all(sg.exp.Table):
        table_name = table_exp.name
        # a CTE name has no schema, so a qualified reference is always a real table
        if not table_name or (not table_exp.db and table_name in cte_aliases):
            continue

        table_ref = frappe._dict(
            name=table_name,
            db=str(table_exp.db) if table_exp.db else None,
            catalog=str(table_exp.catalog) if table_exp.catalog else None,
            reference=table_reference(table_exp),
        )
        ref_key = (table_ref.name, table_ref.db, table_ref.catalog)
        if ref_key in seen_refs:
            continue

        seen_refs.add(ref_key)
        table_refs.append(table_ref)

    return table_refs


def alias_qualified_tables(raw_sql: str, dialect: sg.Dialect | None) -> str:
    """`raw_sql` with each unaliased `schema.table` given an explicit alias, and each
    column that names it pointed at that alias.

    A binding replaces the table with a select, which has no schema. The database
    knows an unaliased `sales.orders` as `orders`, so that stays its alias, and a
    whole-row `orders` still names it. Where another table of the query is also
    known as `orders`, only the schema tells them apart, so the alias is the full
    `"sales.orders"`.
    """
    from sqlglot.optimizer.scope import build_scope

    try:
        parsed = sg.parse_one(raw_sql, dialect=dialect)
    except Exception:
        return raw_sql  # nosemgrep - the database reports a query it cannot parse

    # a CTE name has no schema, so a qualified table is always a real one
    tables = [table for table in parsed.find_all(sg.exp.Table) if table.db and not table.alias]
    if not tables:
        return raw_sql

    root = build_scope(parsed)
    scopes = list(root.traverse()) if root else []
    items = [(scope, item) for scope in scopes for item in from_items(scope)]
    scope_of = {id(item): scope for scope, item in items}
    lineage = {id(scope): ancestors(scope) for scope in scopes}

    # a table shares its name only with the tables of blocks it can see or that
    # can see it: one UNION branch does not see the other's
    def visible_sources(table):
        own = scope_of.get(id(table))
        by_name = {}
        for scope in scopes:
            if own is None or id(own) in lineage[id(scope)] or id(scope) in lineage[id(own)]:
                # as the table sees them: an aliased group hides what it joins
                for item in from_items(scope, table):
                    source = (
                        table_reference(item)
                        if isinstance(item, sg.exp.Table) and not item.alias
                        else id(item)
                    )
                    by_name.setdefault(item.alias_or_name, set()).add(source)
        return by_name

    shared = {}
    for table in tables:
        sources_by_name = visible_sources(table)
        shared[id(table)] = len(sources_by_name.get(table.name, ())) > 1
        # the query's own `"sales.orders"` would then name two tables
        if shared[id(table)] and table_reference(table) in sources_by_name:
            from insights.exceptions import QueryRefused

            frappe.throw(
                frappe._("Rename the alias {0}: it is the full name of a table the query reads").format(
                    table_reference(table)
                ),
                QueryRefused,
                title=frappe._("Unsupported SQL Query"),
            )

    def alias(table):
        if shared[id(table)]:
            return sg.exp.to_identifier(table_reference(table), quoted=True)
        return table.this.copy()

    for scope in scopes:
        for column in scope.find_all(sg.exp.Column):
            if column.table and (table := column_table(scope, column)) in tables:
                column.set("table", alias(table))
                column.set("db", None)

    for table in tables:
        table.set("alias", sg.exp.TableAlias(this=alias(table)))

    return parsed.sql(dialect=dialect)


def ancestors(scope) -> set[int]:
    """The ids of `scope` and of every block that encloses it."""
    ids = set()
    while scope:
        ids.add(id(scope))
        scope = scope.parent
    return ids


def from_items(scope, node: sg.exp.Expression | None = None) -> list[sg.exp.Expression]:
    """The tables, subqueries and lateral joins a query block reads FROM and JOIN, as
    `node` sees them; every one of them, aliased groups included, without it."""
    select = scope.expression
    if not isinstance(select, sg.exp.Select):
        return []
    items = [select.args["from_"].this] if select.args.get("from_") else []
    items += [join.this for join in select.args.get("joins") or []]
    return [table for item in items for table in grouped_join_items(item, node)]


def grouped_join_items(
    item: sg.exp.Expression, node: sg.exp.Expression | None = None
) -> list[sg.exp.Expression]:
    """A `(a JOIN b)` as the items it joins, at any depth. sqlglot parses it as a
    subquery of `a`, with the joins hung on `a` or on the subquery. An aliased
    group hides `a` and `b` behind its alias, except from its own ON clauses."""
    joined = [table for join in item.args.get("joins") or [] for table in grouped_join_items(join.this, node)]
    if isinstance(item, sg.exp.Subquery) and isinstance(item.this, sg.exp.Table | sg.exp.Subquery):
        if item.alias and node is not None and not is_inside(node, item):
            return [item, *joined]
        inner = grouped_join_items(item.this, node)
        return [item, *inner, *joined] if item.alias and node is None else [*inner, *joined]
    return [item, *joined]


def is_inside(node: sg.exp.Expression, ancestor: sg.exp.Expression) -> bool:
    while node is not None:
        if node is ancestor:
            return True
        node = node.parent
    return False


def column_table(scope, column: sg.exp.Column) -> sg.exp.Expression | None:
    """The FROM item a qualified column names, looked up as the database does: in
    the nearest query block outward that has one. A block with two refuses the
    query, as the database would."""
    while scope is not None:
        items = from_items(scope, column)
        if column.args.get("db"):
            sources = [
                item
                for item in items
                if isinstance(item, sg.exp.Table)
                and not item.alias
                and item.db == column.db
                and item.name == column.table
            ]
        else:
            sources = [item for item in items if item.alias_or_name == column.table]

        if len(sources) > 1:
            from insights.exceptions import QueryRefused

            frappe.throw(
                frappe._("{0} could name more than one table").format(column.sql()),
                QueryRefused,
                title=frappe._("Unsupported SQL Query"),
            )
        if sources:
            return sources[0]
        scope = scope.parent
    return None


def table_reference(table_exp: sg.exp.Table) -> str:
    """A table as a SQL query names it, with its schema when the query gives one."""
    return f"{table_exp.db}.{table_exp.name}" if table_exp.db else table_exp.name


def extract_query_deps_from_operations(operations: list) -> list[str]:
    """Extract all referenced query names from a list of operations."""
    return [
        op["table"]["query_name"]
        for op in operations
        if op.get("table")
        and op.get("table", {}).get("type") == "query"
        and op.get("table", {}).get("query_name")
    ]


def referenced_queries(operations) -> set[str]:
    """The query names `operations` references, from a stored or parsed value."""
    return set(extract_query_deps_from_operations(frappe.parse_json(operations) or []))


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

    from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
        db_type_to_sqlglot_dialect,
    )

    seen: set[tuple] = set()
    result = []
    for op in operations:
        if op.get("type") != "sql":
            continue
        raw_sql = op.get("raw_sql") or ""
        ds = op.get("data_source") or ""
        if not raw_sql or not ds:
            continue
        # a deleted data source still names its tables, so a chart reading one stays refused
        data_source = frappe.db.exists("Insights Data Source v3", ds) and frappe.get_cached_doc(
            "Insights Data Source v3", ds
        )
        dialect = db_type_to_sqlglot_dialect(data_source.database_type) if data_source else None
        for ref in extract_sql_table_refs(raw_sql, dialect=dialect):
            # a schema the data source does not read names no table; the run refuses it
            table_name = data_source.sql_table_name(ref.name, ref.db) if data_source else ref.name
            key = (ds, table_name)
            if not table_name or key in seen:
                continue
            seen.add(key)
            result.append({"data_source": ds, "table_name": table_name})
    return result


def table_references(operations) -> list[dict]:
    """The (data_source, table_name) pairs `operations` reads.

    A builder operation names its table outright. A native SQL operation carries
    it in the SQL, so it has to be parsed out.
    """
    ops = frappe.parse_json(operations) or []

    seen: set[tuple] = set()
    result = []
    for ref in extract_table_deps_from_operations(ops) + extract_table_deps_from_sql_operations(ops):
        key = (ref["data_source"], ref["table_name"])
        if key in seen:
            continue
        seen.add(key)
        result.append(ref)
    return result


def sync_query_references(query_name: str, operations) -> None:
    """Rebuild edge rows for *query_name* in Insights Query Reference.

    Deletes all existing outgoing edges for this query then inserts fresh
    rows for every table and query reference found in operations.
    """
    from frappe.model.document import bulk_insert

    ops = frappe.parse_json(operations) or []

    docs = []
    for tbl in table_references(ops):
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

    frappe.db.delete("Insights Query Reference", {"query": query_name})
    if docs:
        bulk_insert("Insights Query Reference", docs)


def query_operations(query_name: str, operations_by_name: dict[str, list] | None = None):
    """A query's stored operations, from a lookup the caller prepared when it has one.

    A caller walking every query on the site reads them all in one go and hands
    the lookup down, so a walk of n hops costs one read instead of n.
    """
    if operations_by_name is not None:
        return operations_by_name.get(query_name)
    return frappe.db.get_value("Insights Query v3", query_name, "operations")


def get_direct_dependencies(query_name: str, operations_by_name: dict[str, list] | None = None) -> list[str]:
    """Return the query names this query directly depends on.

    Read from the query's own `operations`, not from `Insights Query Reference`.
    A forward edge is already in the row, and the edge table is rebuilt by a
    background job that runs after the save commits, so it lags every write.

    Only the edge table answers the reverse question - who references this query.
    `get_lineage_graph` and `get_last_execution_per_table` still read it forwards,
    where a report that lags one job is the whole point of the index.
    """
    if not query_name:
        return []

    return list(referenced_queries(query_operations(query_name, operations_by_name)))


def transitive_closure(
    start: str, start_operations=None, operations_by_name: dict[str, list] | None = None
) -> set[str]:
    """Return all query names reachable from start (not including start itself).

    `start_operations` walks from a document in hand rather than from the row. A
    chart runs a query document that was never saved. Its row then answers with
    another pipeline's operations, or with nothing.
    """
    reachable: set[str] = set()
    stack = (
        list(referenced_queries(start_operations))
        if start_operations is not None
        else get_direct_dependencies(start, operations_by_name)
    )
    while stack:
        node = stack.pop()
        if node in reachable:
            continue
        reachable.add(node)
        stack.extend(get_direct_dependencies(node, operations_by_name))
    return reachable


def source_tables(
    query_name: str, operations=None, operations_by_name: dict[str, list] | None = None
) -> list[dict]:
    """The tables a query reads, through every query it reads."""
    if operations is None:
        operations = query_operations(query_name, operations_by_name)

    reachable = transitive_closure(query_name, operations, operations_by_name)
    pipelines = [operations] + [query_operations(name, operations_by_name) for name in reachable]

    seen: set[tuple] = set()
    tables = []
    for pipeline in pipelines:
        for ref in table_references(pipeline):
            key = (ref["data_source"], ref["table_name"])
            if key in seen:
                continue
            seen.add(key)
            tables.append(ref)
    return tables


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
