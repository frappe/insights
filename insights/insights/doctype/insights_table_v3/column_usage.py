# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Which columns of a table the queries, charts, dashboards and alerts built on it name.

A column is read when its name appears in a reader's stored definition, as a
whole value or bounded by non-identifier characters inside a longer one: an
expression, native SQL, script code. Keys are structure, not names, so they
are not searched.

Compiling the queries would not answer this. ibis lists every column of the
table once a query has a mutate, even under a group by, so the SQL names
columns no author picked. A query with no projection names nothing, so it
reads no column.

The match is by name alone, so a column another table on the chain shares a
name with counts as read. Over-counting keeps a column stored that could go;
under-counting would let a skip break a query.
"""

import json
import re
from collections import defaultdict
from collections.abc import Iterable
from contextlib import suppress

import frappe

QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"
ALERT = "Insights Alert"

IDENTIFIER = re.compile(r"\w+")

TableKey = tuple[str, str]


def get_column_readers(
    data_source: str, table: str, columns: Iterable[str] | None = None
) -> dict[str, list[dict]]:
    """`{column: [{"doctype", "name", "title", "workbook"}]}` for one table.

    `columns` defaults to the table's recorded source columns.
    """
    key = (data_source, table)
    if columns is None:
        columns = get_source_columns([key]).get(key, [])
    return get_column_readers_by_table({key: columns})[key]


def get_column_readers_by_table(
    columns_by_table: dict[TableKey, Iterable[str]],
) -> dict[TableKey, dict[str, list[dict]]]:
    """`get_column_readers` for many tables, reading each definition once."""
    readers = get_readers_by_table(list(columns_by_table))
    return {
        key: {column: [reader.ref for reader in readers[key] if reader.names(column)] for column in columns}
        for key, columns in columns_by_table.items()
    }


def get_source_columns(tables: list[TableKey]) -> dict[TableKey, list[str]]:
    """The column names each table's last import recorded from the source."""
    rows = frappe.get_all(
        "Insights Table v3",
        filters={
            "data_source": ["in", list({ds for ds, _ in tables})],
            "table": ["in", list({t for _, t in tables})],
        },
        fields=["data_source", "table", "columns"],
    )
    wanted = set(tables)
    return {
        (row.data_source, row.table): [c["name"] for c in frappe.parse_json(row.columns or "[]")]
        for row in rows
        if (row.data_source, row.table) in wanted
    }


class Reader:
    def __init__(self, doctype: str, name: str, title: str | None, workbook: str | None, definition):
        self.ref = {"doctype": doctype, "name": name, "title": title or name, "workbook": workbook}
        if isinstance(definition, str):
            with suppress(ValueError):
                definition = json.loads(definition)
        values = list(string_values(definition))
        self.identifiers = {word.lower() for value in values for word in IDENTIFIER.findall(value)}
        self.text = "\n".join(values)

    def names(self, column: str) -> bool:
        if IDENTIFIER.fullmatch(column):
            return column.lower() in self.identifiers
        return bool(re.search(rf"(?<!\w){re.escape(column)}(?!\w)", self.text, re.IGNORECASE))


def string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from string_values(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from string_values(item)


def get_readers_by_table(tables: list[TableKey]) -> dict[TableKey, list[Reader]]:
    """Every reader of each table: the queries that reach it through any number of
    query hops, the charts on those, the dashboards showing the charts, and the
    alerts on the queries.

    Read with `get_all`: a reader the caller may not see still breaks when its
    column goes.
    """
    queries_by_table = get_queries_by_table(tables)
    query_names = set().union(*queries_by_table.values()) if queries_by_table else set()
    if not query_names:
        return {key: [] for key in tables}

    queries = frappe.get_all(
        QUERY,
        filters={"name": ["in", list(query_names)]},
        fields=["name", "title", "workbook", "operations"],
    )
    charts = frappe.get_all(
        CHART,
        filters={"query": ["in", list(query_names)]},
        fields=["name", "title", "workbook", "query", "config"],
    )
    alerts = frappe.get_all(
        ALERT,
        filters={"query": ["in", list(query_names)]},
        fields=["name", "title", "query", "condition", "message"],
    )
    dashboards, charts_by_dashboard = get_dashboards_showing({chart.name for chart in charts})

    workbook_of_query = {q.name: q.workbook for q in queries}
    query_of_chart = {c.name: c.query for c in charts}

    by_query = defaultdict(list)
    for q in queries:
        by_query[q.name].append(Reader(QUERY, q.name, q.title, q.workbook, q.operations))
    for c in charts:
        by_query[c.query].append(Reader(CHART, c.name, c.title, c.workbook, c.config))
    for a in alerts:
        by_query[a.query].append(
            Reader(ALERT, a.name, a.title, workbook_of_query.get(a.query), [a.condition, a.message])
        )
    for d in dashboards:
        reader = Reader(DASHBOARD, d.name, d.title, d.workbook, filter_links(d["items"]))
        for query in {query_of_chart[chart] for chart in charts_by_dashboard[d.name]}:
            by_query[query].append(reader)

    readers = {}
    for key in tables:
        seen = set()
        readers[key] = []
        for query in sorted(queries_by_table.get(key, ())):
            for reader in by_query[query]:
                if id(reader) not in seen:
                    seen.add(id(reader))
                    readers[key].append(reader)
    return readers


def get_queries_by_table(tables: list[TableKey]) -> dict[TableKey, set[str]]:
    """The queries that read each table directly or through other queries.

    One read of the edge table serves every table, as in
    `get_last_execution_per_table`, but walked the other way: from a table to
    the queries that read it, then to the queries that read those.
    """
    references = frappe.get_all(
        "Insights Query Reference",
        fields=["query", "ref_type", "data_source", "table_name", "ref_query"],
    )
    direct: dict[TableKey, set[str]] = defaultdict(set)
    read_by: dict[str, set[str]] = defaultdict(set)
    for ref in references:
        if ref.ref_type == "Table" and ref.table_name:
            direct[(ref.data_source, ref.table_name)].add(ref.query)
        elif ref.ref_type == "Query" and ref.ref_query:
            read_by[ref.ref_query].add(ref.query)

    queries_by_table = {}
    for key in tables:
        reached = set()
        stack = list(direct.get(key, ()))
        while stack:
            query = stack.pop()
            if query in reached:
                continue
            reached.add(query)
            stack.extend(read_by.get(query, ()))
        queries_by_table[key] = reached
    return queries_by_table


def get_dashboards_showing(charts: set[str]) -> tuple[list, dict[str, set[str]]]:
    if not charts:
        return [], {}
    links = frappe.get_all(
        "Insights Dashboard Chart v3",
        filters={"chart": ["in", list(charts)], "parenttype": DASHBOARD},
        fields=["parent", "chart"],
    )
    shown = defaultdict(set)
    for link in links:
        shown[link.parent].add(link.chart)
    if not shown:
        return [], {}
    dashboards = frappe.get_all(
        DASHBOARD,
        filters={"name": ["in", list(shown)]},
        fields=["name", "title", "workbook", "items"],
    )
    return dashboards, shown


def filter_links(items) -> list[str]:
    """The `` `query`.`column` `` links of a dashboard's filters, the only part
    of a dashboard that names a column."""
    return [
        link
        for item in frappe.parse_json(items or "[]")
        if item.get("type") == "filter"
        for link in (item.get("links") or {}).values()
        if isinstance(link, str)
    ]
