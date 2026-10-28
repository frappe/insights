# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Turn what an operator names into the statements to profile.

A dashboard or a chart is loaded through the reader's own code, with the
dashboard's default filters, while `capture` holds every statement back — so
what is profiled is what a reader's load would run, even when nothing ran it
recently or it never once succeeded. A query name, a recorded statement or the
slowest of the week come from what already ran.
"""

import re
from contextlib import suppress
from typing import Any

import frappe

from insights.profiler import capture, events

DASHBOARD = "Insights Dashboard v3"
CHART = "Insights Chart v3"


def resolve(target: dict) -> dict[str, Any]:
    """`{"charts": [...], "statements": [...]}` for one kind of target."""
    if target.get("dashboard"):
        return dashboard_statements(target["dashboard"])
    if target.get("charts"):
        return chart_statements(target["charts"])
    if target.get("queries"):
        return {"charts": [], "statements": [logged(name) for name in target["queries"]]}
    if target.get("statements"):
        return {"charts": [], "statements": [recorded(digest) for digest in target["statements"]]}
    if target.get("slowest"):
        return {"charts": [], "statements": slowest(int(target["slowest"]), int(target.get("days") or 7))}
    frappe.throw(
        frappe._(
            "Name a dashboard, charts, queries, recorded statements, or how many of the slowest to profile"
        )
    )


# --- dashboards and charts ----------------------------------------------------


def dashboard_statements(name: str) -> dict[str, Any]:
    """Every statement the dashboard's charts run when a reader opens it."""
    items = frappe.parse_json(frappe.db.get_value(DASHBOARD, name, "items") or "[]") or []
    charts = [item["chart"] for item in items if item.get("type") == "chart" and item.get("chart")]
    return _collect(charts, dashboard=name, filters=default_filter_states(items))


def chart_statements(charts: list[str]) -> dict[str, Any]:
    return _collect(charts, dashboard=None, filters=None)


def default_filter_states(items: list[dict]) -> dict:
    """The state each dashboard filter opens with, as `defaultFilterStates` sends it.

    A default that needs a value and has none is dropped on the server by
    `_filter_is_set`, as the client drops it.
    """
    return {
        item["filter_name"]: {"operator": item["default_operator"], "value": item.get("default_value")}
        for item in items
        if item.get("type") == "filter" and item.get("filter_name") and item.get("default_operator")
    }


def _collect(charts: list[str], dashboard: str | None, filters: dict | None) -> dict[str, Any]:
    statements: dict[str, dict] = {}
    loaded = []
    for position, chart in enumerate(charts):
        parts, error = _load_chart(chart, dashboard, filters)
        title, chart_type = frappe.db.get_value(CHART, chart, ["title", "chart_type"]) or (None, None)
        loaded.append(
            {
                "position": position,
                "chart": chart,
                "title": title,
                "chart_type": chart_type,
                "error": error,
                "statements": [
                    {"part": part, "digest": _add(statements, found, chart, part)} for part, found in parts
                ],
            }
        )
    return {"charts": loaded, "statements": list(statements.values())}


def _load_chart(chart: str, dashboard: str | None, filters: dict | None) -> tuple[list, str | None]:
    """The statements one chart's load runs, labelled by which part ran them."""
    from insights.api import view

    error = None
    with capture.capturing() as found:
        try:
            view.get_chart_data(chart=chart, dashboard=dashboard, filters=filters)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"[:300]
        from_chart = len(found)
        if frappe.db.get_value(CHART, chart, "chart_type") == "Table":
            # its rows come back empty here, so the count's own read of them may fail
            with suppress(Exception):  # nosemgrep - the statement is captured before it fails
                view.get_chart_count(chart=chart, dashboard=dashboard, filters=filters)
    parts = [
        ("chart" if i == 0 else "sparkline" if i < from_chart else "row count", s)
        for i, s in enumerate(found)
    ]
    return parts, error


def _add(statements: dict[str, dict], found: dict, chart: str, part: str) -> str:
    """Add a captured statement, merging it with an identical one from another chart."""
    digest = events.save_sql(found["sql"])
    entry = statements.setdefault(digest, _statement(found["sql"], found["data_store"], "dashboard"))
    entry["used_by"].append({"chart": chart, "part": part})
    entry["queries"] = sorted({*entry["queries"], found["reference"]} - {None})
    return digest


# --- what already ran ---------------------------------------------------------


def logged(query: str) -> dict:
    """The most recent statement the execution log has for a query."""
    row = frappe.db.sql(
        "SELECT `sql`, data_store FROM `tabInsights Query Execution Log` WHERE query = %s ORDER BY creation DESC LIMIT 1",
        query,
    )
    if not row:
        frappe.throw(frappe._("The execution log has no run of {0}").format(query))
    entry = _statement(row[0][0], bool(row[0][1]), "execution log")
    entry["queries"] = [query]
    return entry


def recorded(digest: str) -> dict:
    """A statement the recorder kept, which may never have succeeded."""
    sql = events.read_sql(digest)
    if sql is None:
        frappe.throw(frappe._("No recorded statement {0}").format(digest))
    return _statement(sql, True, "recorder")


def slowest(limit: int, days: int) -> list[dict]:
    """The worst run of each of the slowest data store queries."""
    rows = frappe.db.sql(
        """
        SELECT l.query, l.`sql`, l.time_taken
        FROM `tabInsights Query Execution Log` l
        JOIN (
            SELECT query, MAX(time_taken) AS worst FROM `tabInsights Query Execution Log`
            WHERE data_store = 1 AND creation > NOW() - INTERVAL %(days)s DAY
            GROUP BY query ORDER BY worst DESC LIMIT %(limit)s
        ) w ON w.query = l.query AND w.worst = l.time_taken
        GROUP BY l.query ORDER BY l.time_taken DESC
        """,
        {"days": days, "limit": max(1, min(limit, 50))},
    )
    return [
        {**_statement(sql, True, "execution log"), "queries": [query], "logged_s": t}
        for query, sql, t in rows
    ]


# --- one statement ------------------------------------------------------------


def _statement(sql: str, data_store: bool, origin: str) -> dict:
    return {
        "digest": events.save_sql(sql),
        "sql": sql,
        "data_store": data_store,
        "origin": origin,
        "shape": shape(sql),
        "used_by": [],
        "queries": [],
    }


def shape(sql: str) -> dict[str, int]:
    """How big and how nested the SQL is — what the planner is handed."""
    depth = deepest = 0
    for char in sql:
        depth += char == "("
        depth -= char == ")"
        deepest = max(deepest, depth)
    count = lambda pattern: len(re.findall(pattern, sql, re.I))
    return {
        "bytes": len(sql),
        "selects": count(r"\bSELECT\b"),
        "joins": count(r"\bJOIN\b"),
        "unions": count(r"\bUNION\b"),
        "ctes": count(r"\bWITH\b"),
        "windows": count(r"\bOVER\s*\("),
        "distincts": count(r"\bDISTINCT\b"),
        "max_nesting": deepest,
    }
