# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Which columns of a table the queries, charts, dashboards, alerts and team
restrictions built on it name.

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

from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.insights.query_utils import (
    referenced_queries,
    table_references,
    unparsed_sql_data_sources,
)

QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"
ALERT = "Insights Alert"
TEAM = "Insights Team"

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
    query hops, the charts on those, the dashboards showing the charts, the
    alerts on the queries, and the teams whose Table Restrictions filter it.

    Read with `get_all`: a reader the caller may not see still breaks when its
    column goes.
    """
    queries = {q.name: q for q in frappe.get_all(QUERY, fields=["name", "title", "workbook", "operations"])}
    queries_by_table = get_queries_by_table(tables, {name: q.operations for name, q in queries.items()})
    query_names = set().union(*queries_by_table.values())

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

    query_of_chart = {c.name: c.query for c in charts}

    by_query = defaultdict(list)
    for name in query_names:
        q = queries[name]
        by_query[name].append(Reader(QUERY, q.name, q.title, q.workbook, q.operations))
    for c in charts:
        by_query[c.query].append(Reader(CHART, c.name, c.title, c.workbook, c.config))
    for a in alerts:
        by_query[a.query].append(
            Reader(ALERT, a.name, a.title, queries[a.query].workbook, [a.condition, a.message])
        )
    for d in dashboards:
        reader = Reader(DASHBOARD, d.name, d.title, d.workbook, filter_links(d["items"]))
        for query in {query_of_chart[chart] for chart in charts_by_dashboard[d.name]}:
            by_query[query].append(reader)

    teams = get_restricting_teams(tables)

    readers = {}
    for key in tables:
        seen = set()
        readers[key] = []
        for query in sorted(queries_by_table[key]):
            for reader in by_query[query]:
                if id(reader) not in seen:
                    seen.add(id(reader))
                    readers[key].append(reader)
        readers[key].extend(teams.get(key, ()))
    return readers


def get_queries_by_table(
    tables: list[TableKey], operations_by_query: dict[str, object]
) -> dict[TableKey, set[str]]:
    """The queries that read each table directly or through other queries.

    Read from each query's own operations, not from `Insights Query Reference`.
    The edge table holds only queries saved since it shipped and keeps rows of
    deleted ones, and a reader it misses would let a skip break a query. For
    the same reason, native SQL sqlglot cannot parse reads every table of its
    data source; the name search still decides which columns it reads.
    """
    wanted = set(tables)
    direct: dict[TableKey, set[str]] = defaultdict(set)
    read_by: dict[str, set[str]] = defaultdict(set)
    for query, operations in operations_by_query.items():
        operations = frappe.parse_json(operations) or []
        for ref in table_references(operations):
            key = (ref["data_source"], ref["table_name"])
            if key in wanted:
                direct[key].add(query)
        for data_source in unparsed_sql_data_sources(operations):
            for key in wanted:
                if key[0] == data_source:
                    direct[key].add(query)
        for source in referenced_queries(operations):
            read_by[source].add(query)

    queries_by_table = {}
    for key in tables:
        reached = set()
        stack = list(direct[key])
        while stack:
            query = stack.pop()
            if query in reached or query not in operations_by_query:
                continue
            reached.add(query)
            stack.extend(read_by[query])
        queries_by_table[key] = reached
    return queries_by_table


def get_restricting_teams(tables: list[TableKey]) -> dict[TableKey, list[Reader]]:
    """The teams whose Table Restrictions filter each table.

    `restriction_predicate` evaluates a restriction over the table's columns,
    so a column it names is read on every query of the team's members.
    """
    names = {get_table_name(*key): key for key in tables}
    rows = frappe.get_all(
        "Insights Resource Permission",
        filters={
            "parenttype": TEAM,
            "resource_type": "Insights Table v3",
            "resource_name": ["in", list(names)],
            "table_restrictions": ["is", "set"],
        },
        fields=["parent", "resource_name", "table_restrictions"],
        order_by="parent asc",
    )
    teams = defaultdict(list)
    for row in rows:
        teams[names[row.resource_name]].append(
            Reader(TEAM, row.parent, row.parent, None, [row.table_restrictions])
        )
    return teams


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
