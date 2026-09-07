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
    doc = {**doc, "workbook": WORKBOOK}
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


# Which config key holds a dimension, and which holds a measure. A measure always
# carries `measure_name`, so it names itself. A dimension often carries only
# `column_name`, and nothing in the node says it is a dimension -- the key does. From
# reference/charts.md, every chart type.
DIMENSION_KEYS = {
    "date_column",
    "x_axis",
    "split_by",
    "dimension",
    "label_column",
    "rows",
    "columns",
    "location_column",
    "source_column",
    "target_column",
}
MEASURE_KEYS = {
    "number_columns",
    "y_axis",
    "series",
    "measure",
    "measures",
    "values",
    "value_column",
    "size_column",
    "xAxis",
    "yAxis",
}


def read_config(config):
    """Three name sets a chart config uses.

    `source` -- names read from the base query: dimensions, measures and chart filters.
    Skips the literal "count" of a row-count measure. An expression measure names no
    column, so it drops out on its own.

    `output` -- names the chart's own aggregation produces. `translate_measure` names a
    measure by `measure_name`. `translate_dimension` names a dimension by
    `dimension_name or column_name`, so a dimension with no `dimension_name` comes out
    under its column name. Granularity keeps the name either way.

    `sorted_by` -- names in `order_by`, which are output names, not source names.
    """
    source, output, sorted_by = set(), set(), set()

    def walk(node, role, in_order_by):
        if isinstance(node, dict):
            name = node.get("column_name")
            if not in_order_by:
                if isinstance(node.get("measure_name"), str):
                    output.add(node["measure_name"])
                elif isinstance(node.get("dimension_name"), str):
                    output.add(node["dimension_name"])
                elif role == "dimension" and isinstance(name, str):
                    output.add(name)
            if isinstance(name, str):
                (sorted_by if in_order_by else source).add(name)
            for key, value in node.items():
                if key in DIMENSION_KEYS:
                    next_role = "dimension"
                elif key in MEASURE_KEYS:
                    next_role = "measure"
                else:
                    next_role = role
                walk(value, next_role, in_order_by or key == "order_by")
        elif isinstance(node, list):
            for item in node:
                walk(item, role, in_order_by)

    walk(config, None, False)
    source.discard("count")
    return source, output, sorted_by


def source_tables(operations):
    """Every real table an operations pipeline reads, as (data_source, table_name)."""
    tables = set()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "table" and node.get("table_name"):
                tables.add((node.get("data_source"), node["table_name"]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(operations)
    return tables


def query_chain(query_name, operations_by_query):
    """A query and every query it reads from, transitively.

    A dashboard filter applies to the query it names, so it only reaches a chart when
    that query is somewhere in the chart's chain.
    """
    chain, pending = set(), [query_name]
    while pending:
        current = pending.pop()
        if current in chain or current not in operations_by_query:
            continue
        chain.add(current)

        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "query" and node.get("query_name"):
                    pending.append(node["query_name"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(operations_by_query[current])
    return chain


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
            "name,title,operations,use_live_connection",
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
            "name,title,query,chart_type,config",
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

    stored = {
        (t["data_source"], t["table_name"])
        for t in (
            call("method", "call", "insights.api.data_store.get_data_store_tables", "-F", "limit=1000") or []
        )
    }
    operations_by_query = {q["name"]: json.loads(q.get("operations") or "[]") for q in queries}

    # Check 1 -- every query builds and runs.
    for q in queries:
        operations = operations_by_query[q["name"]]
        if not operations:
            continue  # a chart's own data_query is empty until the UI opens it
        try:
            result = execute(q["name"])
        except SystemExit as e:
            failures.append(f"query {q['name']} ({q['title']}) did not run: {e}")
            continue
        query_columns[q["name"]] = {c["name"] for c in result["columns"]}
        rows = len(result["rows"])
        print(f"query {q['name']} ({q['title']}): {rows} rows, " f"{len(query_columns[q['name']])} columns")
        if rows:
            continue

        # Zero rows is a real answer on a live query. On a data store query it is not,
        # when a table is still importing: get_ibis_table hands back an empty table with
        # the right schema rather than an error, so the query "succeeds" and reads empty.
        unstored = sorted(t for t in source_tables(operations) if t not in stored)
        if not q.get("use_live_connection") and unstored:
            failures.append(
                f"query {q['name']} ({q['title']}) read zero rows from the data store, and "
                f"{unstored} is not stored yet. The import is queued -- verify again when it "
                "finishes, or set use_live_connection to 1."
            )
        else:
            print("  zero rows -- say so to the user. Only they know whether that is wrong.")

    # Check 2 -- every chart's columns exist in its base query, and it sorts by a name
    # its own aggregation produces.
    for c in charts:
        cols = query_columns.get(c["query"])
        if cols is None:
            failures.append(f"chart {c['name']} ({c['title']}) has no runnable base query")
            continue
        config = json.loads(c.get("config") or "{}")
        source, output, sorted_by = read_config(config)

        missing = sorted(source - cols)
        if missing:
            failures.append(
                f"chart {c['name']} ({c['title']}) names columns its query does not have: "
                f"{missing}. The query has: {sorted(cols)}"
            )

        # A pivoting Table makes its column names out of the data, so they are unknowable here.
        pivots = c.get("chart_type") == "Table" and config.get("columns")
        unknown = sorted(sorted_by - output) if not pivots else []
        if unknown:
            failures.append(
                f"chart {c['name']} ({c['title']}) sorts by {unknown}, which its aggregation does "
                f"not produce. It produces: {sorted(output)}. A sort it cannot resolve is dropped, "
                "so the chart renders in an arbitrary order."
            )

    # Check 3 -- every dashboard reference resolves.
    chart_base_query = {c["name"]: c["query"] for c in charts}
    chart_names = set(chart_base_query)
    for d in dashboards:
        items = json.loads(d.get("items") or "[]")
        seen = set()
        for item in items:
            if item.get("type") == "text":
                # Never author one. But the user may have, and their prose is theirs --
                # failing here would force a delete to make an unrelated edit verify.
                print(
                    f"  note: dashboard {d['name']} has a text item. If you added it, move that "
                    "prose to your reply and remove it. If the user wrote it, leave it alone."
                )

            # The grid reads item.layout.y and item.layout.h for every item, so one item
            # without a layout breaks the whole dashboard, not just itself.
            layout = item.get("layout")
            if not isinstance(layout, dict) or not layout.get("i"):
                failures.append(
                    f"dashboard {d['name']} has an item with no layout.i: {item.get('type')} "
                    f"{item.get('chart') or item.get('filter_name')!r}"
                )
            else:
                if layout["i"] in seen:
                    failures.append(f"dashboard {d['name']} has two items with layout.i {layout['i']!r}")
                seen.add(layout["i"])

            if item.get("type") == "chart" and item.get("chart") not in chart_names:
                failures.append(
                    f"dashboard {d['name']} points at chart {item.get('chart')!r}, "
                    "which is not in this workbook"
                )
            for chart, link in (item.get("links") or {}).items():
                label = f"dashboard {d['name']} filter {item.get('filter_name')!r}"
                if chart not in chart_names:
                    failures.append(f"{label} links chart {chart!r}, which is not in this workbook")
                    continue
                query, _, column = link.strip("`").partition("`.`")
                if column not in query_columns.get(query, set()):
                    failures.append(f"{label} links `{query}`.`{column}`, which that query does not have")
                    continue
                # The filter is appended to the query it names. It reaches the chart only
                # when that query is the chart's base query or feeds it.
                chain = query_chain(chart_base_query[chart], operations_by_query)
                if query not in chain:
                    failures.append(
                        f"{label} links chart {chart!r} to query {query!r}, which that chart does "
                        f"not read from. The filter would do nothing. Its chain is: {sorted(chain)}"
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
