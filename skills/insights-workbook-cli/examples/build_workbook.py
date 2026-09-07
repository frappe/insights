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
# The scratch query. There is no endpoint that samples a raw table, so every
# ad-hoc question runs through one throwaway query in the workbook. Delete it
# before you report -- drop_scratch().
# --------------------------------------------------------------------------

SCRATCH_TITLE = "Scratch — working query, safe to delete"
_scratch = None


def scratch():
    global _scratch
    if _scratch is None:
        _scratch = create(
            "Insights Query v3",
            {
                "title": SCRATCH_TITLE,
                "use_live_connection": 0,
                "is_builder_query": 1,
                "is_native_query": 0,
                "is_script_query": 0,
                "operations": [],
            },
        )
    return _scratch


def probe(operations, page_size=50, use_live_connection=0):
    """Run an ad-hoc pipeline and return its rows. This is check 4's instrument."""
    name = scratch()
    call(
        "doc",
        "update",
        "Insights Query v3",
        name,
        stdin=json.dumps({"operations": operations, "use_live_connection": use_live_connection}),
    )
    return execute(name, page_size=page_size)["rows"]


def distinct_values(query_name, column_name, limit=20):
    """The real values of a column. Runs on a query, not on a table."""
    return call(
        "method",
        "call",
        "get_distinct_column_values",
        "--doctype",
        "Insights Query v3",
        "--name",
        query_name,
        "-F",
        f"column_name={column_name}",
        "-F",
        f"limit={limit}",
    )


def drop_scratch():
    global _scratch
    if _scratch:
        call("doc", "delete", "Insights Query v3", _scratch)
        print(f"scratch deleted {_scratch}")
        _scratch = None


# --------------------------------------------------------------------------
# Dashboard edits. The site owns the layout, so a change is a merge into the
# live `items`, never a fresh array. See reference/dashboards.md.
# --------------------------------------------------------------------------


def item_key(item):
    """What identifies an item across runs. The UI writes its own `layout.i`."""
    if item.get("type") == "chart":
        return ("chart", item.get("chart"))
    if item.get("type") == "filter":
        return ("filter", item.get("filter_name"))
    return ("item", (item.get("layout") or {}).get("i"))


def patch_dashboard(name, upsert=(), drop=()):
    """Merge items into a live dashboard.

    A matched item keeps its live `layout` -- position and size belong to whoever last
    dragged it -- and merges `links` key by key. An unmatched item is appended below the
    current bottom. Everything else on the dashboard is left exactly as it is.

    `drop` takes item_key() tuples. Pass one only when the user asked for that removal.
    """
    doc = call("doc", "get", "Insights Dashboard v3", name)
    doc = doc.get("data", doc)
    items = doc["items"]
    items = json.loads(items) if isinstance(items, str) else items

    live = {item_key(item): item for item in items}
    used_ids = {(i.get("layout") or {}).get("i") for i in items}
    max_y = max((i["layout"]["y"] + i["layout"]["h"] for i in items if i.get("layout")), default=0)

    for new in upsert:
        key = item_key(new)
        old = live.get(key)
        if old is None:
            item = dict(new)
            layout = dict(item.get("layout") or {})
            item_id = layout.get("i") or f"{key[0]}-{key[1]}"
            while item_id in used_ids:
                item_id += "-x"
            layout["i"] = item_id
            used_ids.add(item_id)
            layout.setdefault("x", 0)
            layout.setdefault("y", max_y)
            layout.setdefault("w", 10)
            layout.setdefault("h", 8)
            item["layout"] = layout
            max_y = layout["y"] + layout["h"]
            items.append(item)
            live[key] = item
        else:
            links = dict(old.get("links") or {})
            links.update(new.get("links") or {})
            old.update({k: v for k, v in new.items() if k != "layout"})
            if links:
                old["links"] = links

    if drop:
        items = [i for i in items if item_key(i) not in set(drop)]

    call("doc", "update", "Insights Dashboard v3", name, stdin=json.dumps({"items": items}))
    print(f"dashboard {name} merged, {len(items)} items")


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

    # The whole `items` array is written exactly once, here. Every later change goes
    # through patch_dashboard(), so the user's own layout edits survive.
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
# Verify. Checks 1 to 3 from SKILL.md section 6, as an exit code. Check 4 -- are the
# numbers right -- runs through probe() and needs your judgement on the result.
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
            if item.get("type") == "text":
                failures.append(
                    f"dashboard {d['name']} has a text item -- put that prose in the reply instead"
                )
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

    # Working papers do not ship.
    for q in queries:
        if (q.get("title") or "").startswith("Scratch"):
            failures.append(f"scratch query {q['name']} ({q['title']!r}) is still in the workbook")

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
