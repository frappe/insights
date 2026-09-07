#!/usr/bin/env python3
"""Template for a workbook build. Copy it, edit it, run it.

This is a template, not a library. You own every line. Delete what you do not use.

    python3 build.py            # create, then verify
    python3 build.py --verify   # verify what is already there

Standard library only. `frappectl` prints clean JSON when piped, so it is the client.
"""

import argparse
import json
import subprocess
import sys

SITE = "your-profile"  # the frappectl profile

# The workbook to add to. Set it. Creating a workbook needs the user to ask for one --
# see "Never create a workbook the user did not ask for" in SKILL.md.
WORKBOOK = None


def call(*args, stdin=None):
    """Run frappectl and return its parsed JSON."""
    p = subprocess.run(
        ["frappectl", "-s", SITE, *args],
        input=stdin,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise SystemExit(f"failed: frappectl {' '.join(args)}\n{p.stderr.strip()}")
    return json.loads(p.stdout) if p.stdout.strip() else None


def create(doctype, doc):
    doc["workbook"] = WORKBOOK
    created = call("doc", "create", doctype, stdin=json.dumps(doc))
    name = created["name"] if isinstance(created, dict) else created
    print(f"created {doctype} {name} — {doc.get('title', '')}")
    return name


def execute(query_name, page_size=5):
    return call(
        "method",
        "call",
        "execute",
        "--doctype",
        "Insights Query v3",
        "--name",
        query_name,
        "-F",
        f"page_size={page_size}",
    )


# --------------------------------------------------------------------------
# Build. Queries first, then charts, then dashboards -- each step uses the
# real document names the previous step returned.
# --------------------------------------------------------------------------


def build():
    queries = {}
    charts = {}

    queries["invoices"] = create(
        "Insights Query v3",
        {
            "title": "Sales Invoices",
            # 0 reads the data store, 1 reads the source database. Check
            # get_data_store_tables first -- see SKILL.md section 5.
            "use_live_connection": 0,
            "is_builder_query": 1,
            "is_native_query": 0,
            "is_script_query": 0,
            "operations": [
                {
                    "type": "source",
                    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabSales Invoice"},
                },
                {
                    "type": "filter_group",
                    "logical_operator": "And",
                    "filters": [
                        {
                            "column": {"type": "column", "column_name": "docstatus"},
                            "operator": "=",
                            "value": 1,
                        },
                    ],
                },
            ],
        },
    )

    charts["revenue_trend"] = create(
        "Insights Chart v3",
        {
            "title": "Revenue Trend",
            "query": queries["invoices"],
            "chart_type": "Line",
            "config": {
                "x_axis": {
                    "dimension": {
                        "dimension_name": "posting_date",
                        "column_name": "posting_date",
                        "data_type": "Date",
                        "granularity": "month",
                    }
                },
                "y_axis": {
                    "series": [
                        {
                            "measure": {
                                "measure_name": "Revenue",
                                "column_name": "base_net_total",
                                "data_type": "Decimal",
                                "aggregation": "sum",
                            }
                        }
                    ]
                },
                "order_by": [
                    {"column": {"type": "column", "column_name": "posting_date"}, "direction": "asc"}
                ],
                "limit": 100,
                "filters": {"logical_operator": "And", "filters": []},
            },
        },
    )

    create(
        "Insights Dashboard v3",
        {
            "title": "Sales Overview",
            "items": [
                {
                    "type": "chart",
                    "chart": charts["revenue_trend"],
                    "layout": {"i": "item-revenue-trend", "x": 0, "y": 0, "w": 20, "h": 9},
                },
                {
                    "type": "filter",
                    "filter_name": "Date Range",
                    "filter_type": "Date",
                    "default_operator": "within",
                    "default_value": "Last 12 months",
                    "links": {charts["revenue_trend"]: f"`{queries['invoices']}`.`posting_date`"},
                    "layout": {"i": "filter-date", "x": 0, "y": 9, "w": 4, "h": 1},
                },
            ],
        },
    )


# --------------------------------------------------------------------------
# Verify. The three checks from SKILL.md section 6, as an exit code.
# --------------------------------------------------------------------------


def collect_config_columns(config):
    """Column names a chart config reads from its base query.

    Skips `order_by`, whose names are post-aggregation, and any name that matches a
    measure the config declares. Skips the literal "count" of a row-count measure.
    An expression measure names no column, so it drops out on its own.
    """
    measure_names = set()
    columns = set()

    def walk(node, in_order_by):
        if isinstance(node, dict):
            if "measure_name" in node:
                measure_names.add(node["measure_name"])
            if not in_order_by and isinstance(node.get("column_name"), str):
                columns.add(node["column_name"])
            for key, value in node.items():
                walk(value, in_order_by or key == "order_by")
        elif isinstance(node, list):
            for item in node:
                walk(item, in_order_by)

    walk(config, False)
    return {c for c in columns - measure_names if c != "count"}


def verify():
    failures = []
    query_columns = {}

    queries = (
        call(
            "doc",
            "list",
            "Insights Query v3",
            "-f",
            f"workbook={WORKBOOK}",
            "--fields",
            "name,title,operations",
            "--all",
        )
        or []
    )
    charts = (
        call(
            "doc",
            "list",
            "Insights Chart v3",
            "-f",
            f"workbook={WORKBOOK}",
            "--fields",
            "name,title,query,config",
            "--all",
        )
        or []
    )
    dashboards = (
        call(
            "doc",
            "list",
            "Insights Dashboard v3",
            "-f",
            f"workbook={WORKBOOK}",
            "--fields",
            "name,title,items",
            "--all",
        )
        or []
    )

    # Check 1 -- every query builds and runs.
    for q in queries:
        if not json.loads(q.get("operations") or "[]"):
            continue  # a chart's own data_query is empty until the UI opens it
        try:
            result = execute(q["name"])
        except SystemExit as e:
            failures.append(f"query {q['name']} ({q['title']}) did not run: {e}")
            continue
        query_columns[q["name"]] = {c["name"] for c in result["columns"]}
        rows = len(result["rows"])
        print(f"query {q['name']} ({q['title']}): {rows} rows, " f"{len(query_columns[q['name']])} columns")
        if rows == 0:
            print(
                "  zero rows -- report this to the user. On a data store query it can "
                "mean an import is still running."
            )

    # Check 2 -- every chart's columns exist in its base query.
    for c in charts:
        cols = query_columns.get(c["query"])
        if cols is None:
            failures.append(f"chart {c['name']} ({c['title']}) has no runnable base query")
            continue
        wanted = collect_config_columns(json.loads(c.get("config") or "{}"))
        missing = sorted(wanted - cols)
        if missing:
            failures.append(
                f"chart {c['name']} ({c['title']}) names columns its query does not have: "
                f"{missing}. The query has: {sorted(cols)}"
            )

    # Check 3 -- every dashboard reference resolves.
    chart_names = {c["name"] for c in charts}
    for d in dashboards:
        items = json.loads(d.get("items") or "[]")
        seen = set()
        for item in items:
            i = item.get("layout", {}).get("i")
            if i in seen:
                failures.append(f"dashboard {d['name']} has two items with layout.i {i!r}")
            seen.add(i)
            if item.get("type") == "chart" and item.get("chart") not in chart_names:
                failures.append(
                    f"dashboard {d['name']} points at chart {item.get('chart')!r}, "
                    "which is not in this workbook"
                )
            for chart, link in (item.get("links") or {}).items():
                if chart not in chart_names:
                    failures.append(
                        f"dashboard {d['name']} filter {item.get('filter_name')!r} links "
                        f"chart {chart!r}, which is not in this workbook"
                    )
                    continue
                query, _, column = link.strip("`").partition("`.`")
                if column not in query_columns.get(query, set()):
                    failures.append(
                        f"dashboard {d['name']} filter {item.get('filter_name')!r} links "
                        f"`{query}`.`{column}`, which that query does not have"
                    )

    if failures:
        print("\nFAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="skip the build")
    args = parser.parse_args()

    if not WORKBOOK:
        raise SystemExit("set WORKBOOK to the target workbook name")
    if not args.verify:
        build()
    sys.exit(verify())
