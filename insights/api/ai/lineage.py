# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What a query reads, and what reads it, for an agent about to change the query.

A query is read by other queries, by the charts built on those, and by the
dashboards showing the charts. Rewriting a shared query in place breaks all of
them, and finding them used to take one document read per hop.

Every read goes through `frappe.get_list`, so a document the caller may not read
is never named or counted, and the walk does not pass through it. What reads a
query comes from `Insights Query Reference`, which a job rebuilds after each
save, so a query saved a moment ago may not show downstream yet.
"""

import frappe

from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import LINK_COLUMN
from insights.insights.query_utils import downstream_queries, referenced_queries, table_references
from insights.resolver import not_found

QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"
TABLE = "Insights Table v3"

QUERY_FIELDS = ["name", "title", "workbook", "use_live_connection", "operations"]


@insights_whitelist()
def describe_query(query: str) -> dict:
    """The query, every query and table upstream of it, and everything downstream.

    Upstream is what the query reads: the queries it sources or joins, through
    every hop, and the tables at the end of each, with how the data store keeps
    them. Downstream is what reads it: the queries built on it through every hop,
    the charts on any of those, the dashboards showing those charts, and the
    filter links on those dashboards that name one of those queries.
    """
    rows = frappe.get_list(QUERY, filters={"name": query}, fields=QUERY_FIELDS, limit=1)
    if not rows:
        not_found()

    start = _query_node(rows[0])
    upstream = _walk_upstream(start)
    downstream = _walk_downstream(start)
    _keep_readable_reads([start, *upstream, *downstream])

    read_by_charts = [start.name, *(node.name for node in downstream)]
    charts = charts_reading(read_by_charts, fields=["title"])
    dashboards = dashboards_showing({chart.name for chart in charts}, fields=["title", "workbook", "items"])

    return {
        **start,
        "upstream": {
            "queries": [dict(node) for node in upstream],
            "tables": _tables_read_by([start, *upstream]),
        },
        "downstream": {
            "queries": [dict(node) for node in downstream],
            "charts": [
                {"name": c.name, "title": c.title, "workbook": c.workbook, "query": c.query} for c in charts
            ],
            "dashboards": [
                {"name": d.name, "title": d.title, "workbook": d.workbook, "charts": sorted(d.charts)}
                for d in dashboards
            ],
            "filter_links": _filter_links(dashboards, charts, [start, *downstream]),
        },
    }


def charts_reading(queries, workbooks=(), fields=()) -> list[frappe._dict]:
    """The charts built on `queries` or held by `workbooks`, of those the caller may read."""
    or_filters = {}
    if queries:
        or_filters["query"] = ["in", list(queries)]
    if workbooks:
        or_filters["workbook"] = ["in", list(workbooks)]
    if not or_filters:
        return []

    return frappe.get_list(
        CHART,
        or_filters=or_filters,
        fields=["name", "query", "workbook", *fields],
        limit=0,
    )


def dashboards_showing(charts, fields=()) -> list[frappe._dict]:
    """The dashboards showing any of `charts`, of those the caller may read.

    Each comes with `charts`: those of `charts` it shows. `linked_charts` is an
    edge table, readable by anyone who may read the child doctype, so the
    parents it names are asked for by name before they count.
    """
    if not charts:
        return []

    links = frappe.get_all(
        "Insights Dashboard Chart v3",
        filters={"chart": ["in", list(charts)], "parenttype": DASHBOARD},
        fields=["parent", "chart"],
    )
    if not links:
        return []

    shown = {}
    for link in links:
        shown.setdefault(link.parent, set()).add(link.chart)

    dashboards = frappe.get_list(
        DASHBOARD,
        filters={"name": ["in", list(shown)]},
        fields=["name", *fields],
        limit=0,
    )
    for dashboard in dashboards:
        dashboard.charts = shown[dashboard.name]
    return dashboards


def _query_node(row: frappe._dict) -> frappe._dict:
    operations = frappe.parse_json(row.operations) or []
    return frappe._dict(
        name=row.name,
        title=row.title,
        workbook=row.workbook,
        use_live_connection=bool(row.use_live_connection),
        operations=[operation.get("type") for operation in operations],
        reads=sorted(referenced_queries(operations)),
        tables=table_references(operations),
    )


def _walk_upstream(start: frappe._dict) -> list[frappe._dict]:
    """The queries `start` reads, nearest first."""
    seen = {start.name}
    frontier = set(start.reads) - seen
    found = []
    while frontier:
        seen |= frontier
        rows = frappe.get_list(QUERY, filters={"name": ["in", list(frontier)]}, fields=QUERY_FIELDS, limit=0)
        frontier = set()
        for row in rows:
            node = _query_node(row)
            found.append(node)
            frontier |= set(node.reads) - seen
    return found


def _walk_downstream(start: frappe._dict) -> list[frappe._dict]:
    """The queries that read `start`, nearest first, of those the caller may read."""
    names = downstream_queries(start.name, readable=_readable)
    if not names:
        return []
    rows = frappe.get_list(QUERY, filters={"name": ["in", names]}, fields=QUERY_FIELDS, limit=0)
    by_name = {row.name: row for row in rows}
    return [_query_node(by_name[name]) for name in names]


def _readable(names: set[str]) -> set[str]:
    return set(frappe.get_list(QUERY, filters={"name": ["in", list(names)]}, pluck="name", limit=0))


def _keep_readable_reads(nodes: list[frappe._dict]) -> None:
    """Drop from each node's `reads` the queries the caller may not read."""
    named = {name for node in nodes for name in node.reads}
    known = {node.name for node in nodes}
    unknown = named - known
    readable = known | _readable(unknown) if unknown else known
    for node in nodes:
        node.reads = [name for name in node.reads if name in readable]


def _tables_read_by(nodes: list[frappe._dict]) -> list[dict]:
    """Each table the nodes read, with how the data store keeps it.

    The data store fields are None for a table the caller may not read.
    """
    tables = {}
    for node in nodes:
        for ref in node.tables:
            key = (ref["data_source"], ref["table_name"])
            table = tables.setdefault(
                key,
                {
                    "data_source": key[0],
                    "table_name": key[1],
                    "stored": None,
                    "row_limit": None,
                    "sync_from": None,
                    "read_by": [],
                },
            )
            table["read_by"].append(node.name)

    if not tables:
        return []

    for row in frappe.get_list(
        TABLE,
        filters={
            "data_source": ["in", list({key[0] for key in tables})],
            "table": ["in", list({key[1] for key in tables})],
        },
        fields=["data_source", "table", "stored", "row_limit", "sync_from"],
        limit=0,
    ):
        table = tables.get((row.data_source, row.table))
        if table:
            table.update(stored=bool(row.stored), row_limit=row.row_limit, sync_from=row.sync_from)

    return list(tables.values())


def _filter_links(
    dashboards: list[frappe._dict], charts: list[frappe._dict], lineage: list[frappe._dict]
) -> list[dict]:
    """The filter links on `dashboards` that name a query of `lineage`.

    A link to a chart the dashboard does not show, or to a query the chart does
    not read, filters nothing, so it is left out.
    """
    names = {node.name for node in lineage}
    sources = {node.name: set(node.reads) & names for node in lineage}
    chart_query = {chart.name: chart.query for chart in charts}

    links = []
    for dashboard in dashboards:
        items = frappe.parse_json(dashboard["items"]) or []
        shown = {item.get("chart") for item in items if item.get("type") == "chart"}
        for item in items:
            if item.get("type") != "filter":
                continue
            for chart, link in (item.get("links") or {}).items():
                match = LINK_COLUMN.match(link or "")
                if not match or chart not in shown or chart not in chart_query:
                    continue
                query, column = match.groups()
                if query not in _reached_from(chart_query[chart], sources):
                    continue
                links.append(
                    {
                        "dashboard": dashboard.name,
                        "filter_name": item.get("filter_name"),
                        "chart": chart,
                        "query": query,
                        "column": column,
                    }
                )
    return links


def _reached_from(query: str, sources: dict[str, set[str]]) -> set[str]:
    reached = set()
    stack = [query]
    while stack:
        name = stack.pop()
        if name in reached:
            continue
        reached.add(name)
        stack.extend(sources.get(name, ()))
    return reached
