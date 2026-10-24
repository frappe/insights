# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Verify a workbook in one call, for an agent that has just authored it.

Saving a query, a chart or a dashboard runs nothing: a chart config fails only
when the chart runs, and a filter link names a query and a column nobody
follows. The faults show only when a reader opens the dashboard. So this runs
what a reader runs: each query, each chart through `insights.api.view`, and
each dashboard's charts with its filters routed, and it answers which of them
failed and why.

Column names are resolved by the engine that runs the chart, never by a copy
of its naming rules here. Every document is listed through `frappe.get_list`,
so a document the caller may not read is neither run nor named.
"""

import html

import frappe
from frappe.utils import strip_html

from insights.api import view
from insights.decorators import insights_whitelist
from insights.exceptions import TableNotStored
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
    LINK_COLUMN,
    chart_reads,
    routed_filter_links,
)
from insights.permission_user import runs_as
from insights.resolver import not_found

WORKBOOK = "Insights Workbook"
QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"

QUERY_PAGE_SIZE = 5


@insights_whitelist(methods=["POST"])
def verify_workbook(workbook: str, filters: dict | None = None) -> dict:
    """Run every query, chart and dashboard of a workbook, and report what fails.

    `filters` is dashboard filter state keyed by filter name, the shape
    `insights.api.view.get_chart_data` takes. When given, every chart on every
    dashboard also renders through that dashboard, with the filters that
    dashboard has routed. A filter no dashboard has is an error of the workbook.

    `rows` is the length of one page, never a total: `page_size` rows for a
    query, the chart's own `limit` for a chart.

    A chart's `unresolved_order_by` names the sorts its result has no column
    for, which the engine drops. That fails the chart only when it has a
    `limit`: a top-N without its sort keeps other rows.
    """
    if not frappe.get_list(WORKBOOK, filters={"name": workbook}, pluck="name", limit=1):
        not_found()

    queries = _list(QUERY, workbook, ["name", "title", "use_live_connection", "operations"])
    charts = _list(CHART, workbook, ["name", "title", "query", "config"])
    dashboards = _list(DASHBOARD, workbook, ["name", "title", "items"])

    items = {dashboard.name: dashboard_items(dashboard) for dashboard in dashboards}
    columns = QueryColumns()
    readable_charts = chart_queries(charts, items)
    result = {
        "workbook": workbook,
        "page_size": QUERY_PAGE_SIZE,
        "queries": [verify_query(query, columns) for query in queries],
        "charts": [verify_chart(chart, columns) for chart in charts],
        "dashboards": [
            verify_dashboard(dashboard, items[dashboard.name], readable_charts, columns, filters)
            for dashboard in dashboards
        ],
    }
    filter_names = {item.get("filter_name") for each in items.values() for item in each if is_filter(item)}
    result["errors"] = [
        f"filter {name!r} is on no dashboard of this workbook"
        for name in filters or {}
        if name not in filter_names
    ]
    result["ok"] = not result["errors"] and all(
        entry["ok"] for key in ("queries", "charts", "dashboards") for entry in result[key]
    )
    return result


def _list(doctype: str, workbook: str, fields: list[str]) -> list:
    return frappe.get_list(doctype, filters={"workbook": workbook}, fields=fields, order_by="creation asc")


def dashboard_items(dashboard) -> list[dict]:
    return frappe.parse_json(dashboard.get("items") or "[]") or []


def is_chart(item: dict) -> bool:
    return item.get("type") == "chart"


def is_filter(item: dict) -> bool:
    return item.get("type") == "filter"


def chart_queries(charts: list, items: dict[str, list]) -> dict[str, str]:
    """The query of every chart the caller may read, of the workbook or on its
    dashboards. A dashboard may show a chart of another workbook, and it
    renders there."""
    queries = {chart.name: chart.query for chart in charts}
    shown = {item.get("chart") for each in items.values() for item in each if is_chart(item)}
    if elsewhere := list(shown - set(queries)):
        shown_elsewhere = frappe.get_list(
            CHART, filters={"name": ["in", elsewhere]}, fields=["name", "query"]
        )
        queries.update({chart.name: chart.query for chart in shown_elsewhere})
    return queries


class QueryColumns:
    """The columns of each query run so far, or its error, run at most once.

    A filter link may name a query of another workbook, so a query is looked up
    by name. One the caller may not read answers as missing.
    """

    def __init__(self):
        self.runs = {}

    def run(self, name: str) -> dict:
        if name not in self.runs:
            if not frappe.get_list(QUERY, filters={"name": name}, pluck="name", limit=1):
                self.runs[name] = {"error": "not found"}
            else:
                result, error = attempt(
                    lambda: frappe.get_doc(QUERY, name).execute(
                        page_size=QUERY_PAGE_SIZE, import_if_not_exists=False
                    )
                )
                self.runs[name] = (
                    {"error": error_message(error), "not_stored": isinstance(error, TableNotStored)}
                    if error
                    else result
                )
        return self.runs[name]

    def has_column(self, name: str, column: str) -> bool:
        """Whether a filter on `column` lands on query `name`, by the lookup the
        routed filter itself goes through. Call it only on a query that ran."""
        # asked right after its own build: what a build held back is request state
        builder, _error = attempt(lambda: frappe.get_doc(QUERY, name).get_builder(import_if_not_exists=False))
        return bool(builder) and builder.get_column(column, throw=False) is not None


def verify_query(query, columns: QueryColumns) -> dict:
    """One query's run. A Data Store table it reads that is not stored yet fails
    it: the run would read an empty table in its place."""
    run = columns.run(query.name)
    entry = {"name": query.name, "title": query.title, "ok": not run.get("error")}
    if run.get("error"):
        entry["error"] = run["error"]
    else:
        entry["rows"] = len(run["rows"])
        entry["columns"] = [column["name"] for column in run["columns"]]
    return entry


def verify_chart(chart, columns: QueryColumns) -> dict:
    """Run a chart as a reader does."""
    entry = {"name": chart.name, "title": chart.title, "query": chart.query}
    entry.update(chart_run(chart.query, columns, lambda: view.get_chart_data(chart=chart.name)))
    entry["ok"] = not entry.get("errors")
    if entry["ok"] and (unresolved := unresolved_order_by(chart.name)):
        entry["unresolved_order_by"] = unresolved
        entry["ok"] = not frappe.parse_json(chart.config or "{}").get("limit")
    return entry


def unresolved_order_by(name: str) -> list[str]:
    """The sorts of a chart that `apply_order_by` drops, because the column it
    looks up is not on the chart's result."""
    chart = frappe.get_doc(CHART, name)
    operations = chart.get_operations()
    sorts = [
        operation["column"]["column_name"] for operation in operations if operation["type"] == "order_by"
    ]
    if not sorts:
        return []
    with runs_as(chart):
        builder, _error = attempt(lambda: chart.get_query(operations).get_builder(import_if_not_exists=False))
        if not builder:
            return []
        return [column for column in sorts if builder.get_column(column, throw=False) is None]


def chart_run(query: str | None, columns: QueryColumns, run) -> dict:
    """What one chart run says: its row count, or why it has none.

    A reader's run imports a table that is not stored and reads it empty, so a
    chart whose query reads one fails as its query does, and is not run.
    """
    if query and (query_run := columns.run(query)).get("not_stored"):
        return {"errors": [query_run["error"]]}
    answer, error = attempt(run)
    if error:
        return {"errors": [error_message(error)]}
    if answer.get("errors"):
        return {"errors": answer["errors"]}
    if refusal := answer.get("not_permitted"):
        return {"errors": [f"not permitted: needs read access to {', '.join(refusal['doctypes'])}"]}
    return {"rows": len(answer["rows"])}


def verify_dashboard(
    dashboard, items: list[dict], readable_charts: dict[str, str], columns: QueryColumns, filters: dict | None
):
    on_dashboard = {item.get("chart") for item in items if is_chart(item)}
    errors = []

    for position, item in enumerate(items):
        label = item_label(position, item)
        if is_chart(item) and item.get("chart") not in readable_charts:
            errors.append(f"{label} is not a chart you may read")

        if is_filter(item):
            errors += link_errors(label, item, on_dashboard, columns)

    entry = {"name": dashboard.name, "title": dashboard.title}
    if filters:
        filter_names = {item.get("filter_name") for item in items if is_filter(item)}
        own_filters = {name: state for name, state in filters.items() if name in filter_names}
        entry["charts"] = [
            render_chart(chart, readable_charts[chart], dashboard, items, own_filters, columns)
            for chart in dict.fromkeys(item.get("chart") for item in items if is_chart(item))
            if chart in readable_charts
        ]

    entry["errors"] = errors
    entry["ok"] = not errors and all(chart["ok"] for chart in entry.get("charts", []))
    return entry


def item_label(position: int, item: dict) -> str:
    name = item.get("chart") or item.get("filter_name")
    return f"item {position} ({item.get('type')}{f' {name!r}' if name else ''})"


def link_errors(label: str, item: dict, on_dashboard: set, columns: QueryColumns) -> list[str]:
    """Why a filter's links would not narrow the charts they name.

    `chart_reads` is the rule the routing itself applies: a filter lands on the
    query its link names, so a query outside the chart's chain changes nothing.
    """
    errors = []
    for chart, link in (item.get("links") or {}).items():
        match = LINK_COLUMN.match(link or "")
        if chart not in on_dashboard:
            errors.append(f"{label} links chart {chart!r}, which is not on this dashboard")
            continue
        if not match:
            errors.append(f"{label} links chart {chart!r} by {link!r}, which is not `query`.`column`")
            continue

        query, column = match.groups()
        if not chart_reads(chart, query):
            errors.append(f"{label} links chart {chart!r} to query {query!r}, which that chart does not read")
            continue
        if columns.run(query).get("error"):
            errors.append(f"{label} links query {query!r}, which did not run")
        elif not columns.has_column(query, column):
            errors.append(f"{label} links column {column!r}, which query {query!r} does not have")
    return errors


def render_chart(chart: str, query: str | None, dashboard, items: list, filters: dict, columns: QueryColumns):
    """A chart as the dashboard's reader gets it with these filters set."""
    entry = {
        "name": chart,
        "filters": list(dict.fromkeys(name for name, *_ in routed_filter_links(items, chart, filters))),
        **chart_run(
            query,
            columns,
            lambda: view.get_chart_data(chart=chart, dashboard=dashboard.name, filters=filters),
        ),
    }
    entry["ok"] = not entry.get("errors")
    return entry


def attempt(run):
    """`(result, None)`, or `(None, error)` when `run` raises.

    A failure is part of the report, so the response's message log is put back
    as it was, where every failure would otherwise arrive a second time. The run
    may rebind the log, as `frappe.clear_last_message` does, so it is restored,
    not truncated.
    """
    message_log = list(getattr(frappe.local, "message_log", None) or [])
    try:
        return run(), None
    except Exception as e:
        return None, e
    finally:
        frappe.local.message_log = message_log


def error_message(error: Exception) -> str:
    # `frappe.throw` puts its message in `args`; the `str` of a `KeyError` quotes
    # it and an `OSError`'s reformats it. The message carries HTML for the UI
    message = getattr(error, "operation_message", None) or (
        error.args[0] if error.args and isinstance(error.args[0], str) else str(error)
    )
    return html.unescape(strip_html(message)) or type(error).__name__
