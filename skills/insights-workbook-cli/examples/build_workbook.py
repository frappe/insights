#!/usr/bin/env python3
"""A workbook build, and the helpers it runs on. Copy it and edit build(), or import it.

    python3 build.py --site <profile> --workbook <name>              # build, then verify
    python3 build.py --site <profile> --workbook <name> --verify     # verify only
    python3 build.py --site <profile> --workbook <name> --redesign   # replace dashboard items

`--site` and `--workbook` fall back to the SITE and WORKBOOK environment variables.

Rerun it as often as you like. The build keeps a state file next to the script. It maps each
key to its document name and to what the build last wrote. A rerun updates in place, and
leaves alone a field the user edited on the site since.

From another script:

    import build_workbook as bw
    bw.configure("<profile>", "<workbook>")
    bw.run([{"type": "source", "table": {...}}])["rows"]
    bw.Build().upsert("<key>", bw.QUERY, {...})
    bw.verify()

Standard library only. `frappectl` prints clean JSON when piped, so it is the client.
"""

import argparse
import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path

QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"

JSON_FIELDS = {"operations": list, "config": dict, "items": list}

SITE = os.environ.get("SITE")  # the frappectl profile
# The workbook to add to. Creating a workbook needs the user to ask for one --
# see "Never create a workbook the user did not ask for" in SKILL.md.
WORKBOOK = os.environ.get("WORKBOOK")


class CallFailed(Exception):
    pass


class TableNotStored(CallFailed):
    """A probe on the data store read a table that is not stored. No import was queued."""


def configure(site=None, workbook=None):
    global SITE, WORKBOOK
    SITE = site or SITE
    WORKBOOK = workbook or WORKBOOK
    if not SITE or not WORKBOOK:
        raise CallFailed("set the site and the workbook: --site and --workbook, or SITE and WORKBOOK")


# --------------------------------------------------------------------------
# The client
# --------------------------------------------------------------------------


def clean_stderr(text):
    """stderr without the deprecation warning authlib prints on every frappectl call."""
    kept, in_warning = [], False
    for line in text.splitlines():
        if "DeprecationWarning" in line:
            in_warning = True
            continue
        if in_warning and line.startswith((" ", "\t")):
            continue
        in_warning = False
        kept.append(line)
    return "\n".join(kept).strip()


def call(*args, stdin=None, allow_empty=False):
    """Run frappectl and return its parsed JSON.

    An empty or non-JSON stdout is a failure: it is how an expired session shows.
    """
    if not SITE:
        raise CallFailed("no site: call configure() first")
    p = subprocess.run(["frappectl", "-s", SITE, *args], input=stdin, capture_output=True, text=True)
    command = f"frappectl {' '.join(args)}"
    stderr = clean_stderr(p.stderr)
    if p.returncode != 0:
        raise CallFailed(f"failed: {command}\n{stderr}")
    if not p.stdout.strip():
        if allow_empty:
            return None
        raise CallFailed(f"no output: {command}\n{stderr or 'stderr is empty. Check auth whoami.'}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        raise CallFailed(f"not JSON: {command}\n{p.stdout[:500]}\n{stderr}") from None


_methods = {}
_read_only = None


def read_only():
    """Whether the profile sends only GET, so a POST-only method is out of its reach."""
    global _read_only
    if _read_only is None:
        _read_only = bool(call("auth", "whoami").get("read_only"))
    return _read_only


def has_method(path):
    """Whether the site has a whitelisted method. Asked once per run.

    The probe calls the method with no arguments. Only a missing method answers
    "Failed to get method". A missing-argument error means it is there, and so
    does a POST-only method's refusal of a read-only profile's GET.
    """
    if path not in _methods:
        try:
            call("method", "call", path)
            _methods[path] = True
        except CallFailed as e:
            _methods[path] = "Failed to get method" not in " ".join(str(e).split())
    return _methods[path]


def method(path, **fields):
    """Call a whitelisted method. Every field goes as raw JSON, so its type survives."""
    args = []
    for key, value in fields.items():
        if value is not None:
            args += ["-F", f"{key}:={json.dumps(value)}"]
    return call("method", "call", path, *args)


def decode(doc):
    """A document as `doc get` or `doc list` returns it, with its JSON fields parsed."""
    if isinstance(doc.get("data"), dict):
        doc = doc["data"]
    doc = dict(doc)
    for field, empty in JSON_FIELDS.items():
        if field in doc:
            value = doc[field]
            if isinstance(value, str):
                value = json.loads(value) if value.strip() else None
            doc[field] = empty() if value is None else value
    return doc


def get_doc(doctype, name, missing_ok=False):
    """One document. `doc get` omits a null field, so read every field with .get()."""
    try:
        return decode(call("doc", "get", doctype, name))
    except CallFailed as e:
        text = str(e).lower()
        if missing_ok and ("not found" in text or "doesnotexist" in text or "does not exist" in text):
            return None
        raise


def list_docs(doctype, fields, filters=()):
    """The documents of WORKBOOK. One --filters-json, because frappectl lets it replace every -f."""
    fields = sorted({"name", "workbook", *fields})
    rows = call(
        "doc",
        "list",
        doctype,
        "--filters-json",
        json.dumps([["workbook", "=", WORKBOOK], *filters]),
        "--fields",
        ",".join(fields),
        "--all",
    )
    rows = [decode(row) for row in rows or []]
    for row in rows:
        for field, empty in JSON_FIELDS.items():
            if field in fields and field not in row:
                row[field] = empty()
    strangers = [row["name"] for row in rows if row.get("workbook") != WORKBOOK]
    if strangers:
        raise CallFailed(f"{doctype} list returned documents of another workbook: {strangers}")
    return rows


def assert_in_workbook(doctype, live):
    if live.get("workbook") != WORKBOOK:
        raise CallFailed(
            f"{doctype} {live.get('name')} is in workbook {live.get('workbook')!r}, not {WORKBOOK!r}"
        )


def create(doctype, doc):
    doc = {**doc, "workbook": WORKBOOK}
    created = call("doc", "create", doctype, stdin=json.dumps(doc))
    if isinstance(created, dict):
        created = created.get("data", created)["name"]
    print(f"created {doctype} {created} -- {doc.get('title', '')}")
    return created


def update(doctype, name, patch, live=None):
    """Patch a document. Refuses one that is not in WORKBOOK."""
    assert_in_workbook(doctype, live or get_doc(doctype, name))
    return call("doc", "update", doctype, name, stdin=json.dumps(patch))


def delete(doctype, name):
    assert_in_workbook(doctype, get_doc(doctype, name))
    call("doc", "delete", doctype, name, allow_empty=True)


def query_call(name, query_name, *fields):
    """Call a method of a saved query. A POST asks for write on it, so this sends GET."""
    return call("method", "call", name, "--doctype", QUERY, "--name", query_name, "-X", "GET", *fields)


def execute(query_name, page_size=5):
    """Run a saved query."""
    return query_call("execute", query_name, "-F", f"page_size={page_size}")


def run_chart(chart_name):
    """Run a saved chart. Saving does not validate its config, so this is the only check."""
    return call("method", "call", "insights.api.view.get_chart_data", "-F", f"chart={chart_name}")


# --------------------------------------------------------------------------
# Probes. An unsaved pipeline runs as a query document that is never saved, the
# way the Builder runs one. It writes nothing, so a read-only profile runs it too.
# --------------------------------------------------------------------------

RUN_DOC_METHOD = "insights.api.run_doc_method"
VERIFY_WORKBOOK = "insights.api.ai.verify.verify_workbook"
# the query method profile_column arrived with verify_workbook
PROFILE_COLUMN = VERIFY_WORKBOOK
# `execute` answers 10,000 rows at most, and a run asks for one more than the page
MAX_PAGE_SIZE = 9_999
NOT_STORED = re.compile(r": TableNotStored\b")


def not_stored(error):
    return bool(NOT_STORED.search(error or ""))


def query_sources(operations):
    """The saved queries a pipeline reads."""
    names = set()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "query" and node.get("query_name"):
                names.add(node["query_name"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(operations)
    return names


def unsaved_query(operations, use_live_connection):
    """An `Insights Query v3` of WORKBOOK that is never saved. A `new-` name has no row behind it."""
    return {
        "doctype": QUERY,
        "name": "new-insights-query-v3-1",
        "__islocal": 1,
        "workbook": WORKBOOK,
        "is_builder_query": 1,
        "use_live_connection": int(bool(use_live_connection)),
        "operations": operations,
    }


def query_method(name, query=None, docs=None, **args):
    """Run a query document method, on the saved `query` or on the unsaved `docs`.

    It never queues an import: a data store table that is not stored raises TableNotStored.
    `profile_column` never imports, so only `execute` is told.
    """
    args = {key: value for key, value in args.items() if value is not None}
    if name == "execute":
        args["import_if_not_exists"] = False
    try:
        if query:
            fields = [f for key, value in args.items() for f in ("-F", f"{key}:={json.dumps(value)}")]
            return query_call(name, query, *fields)
        return method(RUN_DOC_METHOD, method=name, docs=docs, args=args)
    except CallFailed as e:
        if not_stored(str(e)):
            raise TableNotStored(str(e)) from None
        raise


def run(operations, page_size=50, use_live_connection=1, force=False):
    """Run an unsaved pipeline and return what `execute` returns: `columns`, `rows`, `sql`,
    plus `truncated`, which says the result has more rows than the page.

    This is check 4's instrument. `force` skips the site's 10-minute cache. Raises
    TableNotStored when a data store table it reads is not stored.
    """
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    docs = unsaved_query(operations, use_live_connection)
    result = query_method("execute", docs=docs, page_size=page_size + 1, force=force or None)
    result["truncated"] = len(result["rows"]) > page_size
    result["rows"] = result["rows"][:page_size]
    return result


def profile(column, query=None, operations=None, by=None, limit=20, use_live_connection=1, force=False):
    """What the values of `column` look like, in a saved `query` or in `operations`.

    Returns row_count, null_count, distinct_count, min, max and top_values [{value, count,
    share}]. With `by`, also coverage [{value, row_count, non_null_count, share}]: per value
    of `by`, the share of rows with a value in `column`. `column` and `by` are exact column
    names. `force` skips the site's 10-minute cache. Raises TableNotStored as run() does.
    """
    if has_method(PROFILE_COLUMN):
        docs = None if query else unsaved_query(operations, use_live_connection)
        return query_method(
            "profile_column", query, docs, column_name=column, by=by, limit=limit, force=force or None
        )

    if query:
        operations = [
            {"type": "source", "table": {"type": "query", "workbook": WORKBOOK, "query_name": query}}
        ]
        use_live_connection = get_doc(QUERY, query).get("use_live_connection") or 0

    def measure(name, expression, data_type="Integer"):
        return {
            "measure_name": name,
            "data_type": data_type,
            "expression": {"type": "expression", "expression": expression},
        }

    def summarize(measures, dimension=None):
        dimensions = (
            [{"dimension_name": "value", "column_name": dimension, "data_type": "String"}]
            if dimension
            else []
        )
        steps = [*operations, {"type": "summarize", "measures": measures, "dimensions": dimensions}]
        if dimension:
            steps += [
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "row_count"},
                    "direction": "desc",
                },
                {"type": "limit", "limit": limit},
            ]
        return run(steps, page_size=limit, use_live_connection=use_live_connection, force=force)["rows"]

    def share(part, whole):
        return part / whole if whole else None

    col = f"q[{column!r}]"
    summary = summarize(
        [
            measure("row_count", "count()"),
            measure("non_null_count", f"count({col})"),
            measure("distinct_values", f"distinct_count({col})"),
            measure("min_value", f"min({col})", "String"),
            measure("max_value", f"max({col})", "String"),
        ]
    )[0]
    row_count = summary["row_count"] or 0
    result = {
        "column": column,
        "row_count": row_count,
        "null_count": row_count - (summary["non_null_count"] or 0),
        "distinct_count": summary["distinct_values"],
        "min": summary["min_value"],
        "max": summary["max_value"],
        "top_values": [
            {"value": r["value"], "count": r["row_count"], "share": share(r["row_count"], row_count)}
            for r in summarize([measure("row_count", "count()")], column)
        ],
    }
    if by:
        result["by"] = by
        result["coverage"] = [
            {**r, "share": share(r["non_null_count"], r["row_count"])}
            for r in summarize(
                [measure("row_count", "count()"), measure("non_null_count", f"count({col})")], by
            )
        ]
    return result


def distinct_values(query_name, column_name, limit=20):
    """The real values of a column. Runs on a saved query, not on a table."""
    return query_call(
        "get_distinct_column_values", query_name, "-F", f"column_name={column_name}", "-F", f"limit={limit}"
    )


# --------------------------------------------------------------------------
# Dashboard edits. The site owns the layout, so a change is a merge into the
# live `items`, never a fresh array. See reference/dashboards.md.
# --------------------------------------------------------------------------


def item_key(item):
    """What identifies an item across runs. The UI writes its own `layout.i`.

    A Number chart draws one cell per reading, every one of them naming the same
    chart, so its `reading` is part of the key.
    """
    if item.get("type") == "chart":
        return ("chart", item.get("chart"), item.get("reading"))
    if item.get("type") == "filter":
        return ("filter", item.get("filter_name"))
    return ("item", (item.get("layout") or {}).get("i"))


GRID_COLUMNS = 20
FILTER_WIDTH, FILTER_ROWS = 4, 2
CHART_WIDTH, CHART_ROWS = 10, 20
READING_WIDTH, READING_ROWS = 4, 5
# A row is 22px. One line of an <h1> to <h3> is at most 28px, and the cell pads 16px.
HEADING_WIDTH, HEADING_ROWS = GRID_COLUMNS, 2


def filter_layout(items):
    """Where the app puts a new filter: right of the last filter in the top filter row.

    No chart may share a row with a filter. When that row is full or there is no
    filter, the new one takes x:0 y:0 and every other item moves down a filter row.
    """
    filters = [i["layout"] for i in items if i.get("type") == "filter" and i.get("layout")]
    if filters:
        top = min(f["y"] for f in filters)
        right = max(f["x"] + f["w"] for f in filters if f["y"] == top)
        if right + FILTER_WIDTH <= GRID_COLUMNS:
            return {"x": right, "y": top, "w": FILTER_WIDTH, "h": FILTER_ROWS}
    for item in items:
        if item.get("layout"):
            item["layout"]["y"] += FILTER_ROWS
    return {"x": 0, "y": 0, "w": FILTER_WIDTH, "h": FILTER_ROWS}


def merge_items(items, upsert=(), drop=()):
    """Merge items into a dashboard's `items`. Returns a new list.

    A matched item keeps its live `layout` and `layouts` -- position and size belong to
    whoever last dragged it -- and merges `links` key by key. A new filter goes in the
    top filter row. A new chart or heading is appended below the current bottom, and the
    readings of one Number chart sit side by side. A layout field the new item sets wins.
    Everything else is left exactly as it is.

    `drop` takes item_key() tuples. Pass one only when the user asked for that removal.
    """
    items = copy.deepcopy(list(items))
    live = {item_key(item): item for item in items}
    used_ids = {(i.get("layout") or {}).get("i") for i in items}
    last = None  # the item appended last, so the next reading can sit beside it

    for new in upsert:
        key = item_key(new)
        old = live.get(key)
        if old is None:
            item = copy.deepcopy(new)
            layout = dict(item.get("layout") or {})
            item_id = layout.get("i") or re.sub(
                r"[^a-z0-9]+", "-", "-".join(str(k) for k in key if k).lower()
            )
            while item_id in used_ids:
                item_id += "-x"
            used_ids.add(item_id)
            if item.get("type") == "filter":
                if "y" not in layout:
                    layout = {**filter_layout(items), **layout}
            else:
                max_y = max(
                    (i["layout"]["y"] + i["layout"]["h"] for i in items if i.get("layout")), default=0
                )
                reading = bool(item.get("reading"))
                if item.get("type") == "text":
                    w, h = HEADING_WIDTH, HEADING_ROWS
                elif reading:
                    w, h = READING_WIDTH, READING_ROWS
                else:
                    w, h = CHART_WIDTH, CHART_ROWS
                x, y = 0, max_y
                if reading and last and last.get("reading"):
                    beside = last["layout"]["x"] + last["layout"]["w"]
                    if beside + w <= GRID_COLUMNS:
                        x, y = beside, last["layout"]["y"]
                layout = {"x": x, "y": y, "w": w, "h": h, **layout}
                last = item
            layout["i"] = item_id
            item["layout"] = layout
            items.append(item)
            live[key] = item
        else:
            links = dict(old.get("links") or {})
            links.update(new.get("links") or {})
            old.update({k: v for k, v in new.items() if k not in ("layout", "layouts")})
            if links:
                old["links"] = links

    if drop:
        drop = set(drop)
        items = [i for i in items if item_key(i) not in drop]
    return items


def patch_dashboard(name, upsert=(), drop=()):
    """Merge items into a live dashboard. See merge_items()."""
    live = get_doc(DASHBOARD, name)
    items = merge_items(live.get("items") or [], upsert, drop)
    update(DASHBOARD, name, {"items": items}, live=live)
    print(f"dashboard {name} merged, {len(items)} items")
    return items


def item_changes(desired, sent):
    """The items of `desired` the build did not send last time, for merge_items().

    An item the build sent before goes as its key and the fields changed since, so a
    field the user edited and the build did not change keeps the user's value.
    """
    sent_by_key = {item_key(item): item for item in sent}
    changes = []
    for item in desired:
        before = sent_by_key.get(item_key(item))
        if before is None:
            changes.append(item)
        elif before != item:
            keys = ("type", "chart", "reading", "filter_name", "layout")
            changes.append({k: v for k, v in item.items() if k in keys or before.get(k) != v})
    return changes


# --------------------------------------------------------------------------
# Upsert. The state file holds, per key, the document name and per field two
# values: `sent`, what the build asked for, and `stored`, what the site held
# right after. A live value that differs from `stored` is the user's edit.
# --------------------------------------------------------------------------


def blank(value):
    return value is None or value == "" or value == [] or value == {}


def same(a, b):
    return (blank(a) and blank(b)) or a == b


def default_state_path():
    script = Path(sys.argv[0]) if sys.argv and sys.argv[0].endswith(".py") else Path(__file__)
    return script.resolve().with_name(script.stem + ".state.json")


class Build:
    def __init__(self, state_path=None, redesign=False):
        self.path = Path(state_path) if state_path else default_state_path()
        self.redesign = redesign
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.kept = []

    @property
    def entries(self):
        return self.state.setdefault(SITE, {}).setdefault(WORKBOOK, {})

    def save(self):
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.state, indent=1, sort_keys=True, ensure_ascii=False))
        os.replace(tmp, self.path)

    def upsert(self, key, doctype, fields):
        """Create the document behind `key`, or update it in place. Returns its name.

        A field the user edited since the last run keeps the user's value and is printed.
        A dashboard's `items` go through the merge. With `redesign` they are replaced whole,
        but only while the live items still equal what the build last wrote.
        """
        entry = self.entries.get(key)
        live = get_doc(doctype, entry["name"], missing_ok=True) if entry else None
        if entry and live is None:
            print(f"{doctype} {entry['name']} ({key}) is gone from the site. Creating it again.")

        if live is None:
            doc = dict(fields)
            if doctype == DASHBOARD and "items" in doc:
                doc["items"] = merge_items([], doc["items"])
            name = create(doctype, doc)
            entry = self.entries[key] = {"doctype": doctype, "name": name, "sent": {}, "stored": {}}
            written = set(fields)
        else:
            assert_in_workbook(doctype, live)
            name = entry["name"]
            patch = self.changes(key, doctype, fields, live, entry)
            if patch:
                update(doctype, name, patch, live=live)
                print(f"updated {doctype} {name} ({key}): {', '.join(sorted(patch))}")
            written = set(patch) | {f for f in fields if same(live.get(f), fields[f])}

        after = get_doc(doctype, name)
        for field in written:
            entry["sent"][field] = fields[field]
            entry["stored"][field] = after.get(field)
        self.save()
        return name

    def changes(self, key, doctype, fields, live, entry):
        patch = {}
        for field, value in fields.items():
            if field == "items" and doctype == DASHBOARD:
                items = self.items_patch(key, value, live, entry)
                if items is not None:
                    patch["items"] = items
                continue
            current = live.get(field)
            if field in entry["stored"]:
                if not same(current, entry["stored"][field]):
                    self.keep(doctype, live["name"], key, field)
                    continue
                if same(value, entry["sent"].get(field)):
                    continue
            elif not blank(current) and not same(current, value):
                # the build never wrote this field, so its value on the site is someone's
                self.keep(doctype, live["name"], key, field)
                continue
            if not same(current, value):
                patch[field] = value
        return patch

    def items_patch(self, key, desired, live, entry):
        sent = entry["sent"].get("items") or []
        if desired == sent:
            return None
        live_items = live.get("items") or []
        label = f"dashboard {live['name']} ({key})"
        if self.redesign:
            if "items" in entry["stored"] and live_items == entry["stored"]["items"]:
                return merge_items([], desired)
            print(f"{label}: the items changed on the site since the last run. Merging, not replacing.")
        for k in sorted({item_key(i) for i in sent} - {item_key(i) for i in desired}, key=str):
            print(f"{label}: {k} left the build but stays on the dashboard. Drop it only if the user asked.")
        return merge_items(live_items, item_changes(desired, sent))

    def keep(self, doctype, name, key, field):
        self.kept.append((doctype, name, key, field))
        print(f"kept {doctype} {name} ({key}) {field}: edited on the site, left as the user set it")


# --------------------------------------------------------------------------
# Build. Queries first, then charts, then dashboards -- each step uses the
# real document names the previous step returned. The keys are yours. Keep
# them stable across runs: a key is what finds its document again.
# --------------------------------------------------------------------------


def build(b):
    invoices = b.upsert(
        "invoices",
        QUERY,
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

    revenue = b.upsert(
        "revenue",
        CHART,
        {
            "title": "Revenue",
            "query": invoices,
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

    # `items` is the design. The first run writes it whole, placed as the app places a new
    # item. A rerun merges only what changed here into the live items.
    b.upsert(
        "sales_overview",
        DASHBOARD,
        {
            "title": "Sales Overview",
            "items": [
                {
                    "type": "filter",
                    "filter_name": "Date Range",
                    "filter_type": "Date",
                    "links": {revenue: f"`{invoices}`.`posting_date`"},
                },
                {"type": "text", "text": "<h3>Revenue</h3>", "layout": {"i": "heading-revenue"}},
                {"type": "chart", "chart": revenue, "layout": {"w": 20}},
            ],
        },
    )


# --------------------------------------------------------------------------
# Verify. Checks 1 to 3 from SKILL.md section 6, as an exit code. Check 4 -- are the
# numbers right -- runs through run() and profile() and needs your judgement.
# --------------------------------------------------------------------------


def verify(filters=None):
    """Checks 1 to 3. Returns 0 when the workbook verifies clean, else 1.

    `filters` is dashboard filter state by filter name, as get_chart_data takes it. A
    newer site then also renders each dashboard's charts under the filters it has.
    """
    if not read_only() and has_method(VERIFY_WORKBOOK):
        return report(method(VERIFY_WORKBOOK, workbook=WORKBOOK, filters=filters))
    return verify_locally()


def report(result):
    """Print a verify_workbook result. Returns the exit code."""
    failures = list(result.get("errors") or [])
    for q in result.get("queries", []):
        label = f"query {q['name']} ({q.get('title')})"
        if q.get("error"):
            hint = (
                ". Store the table first, or set use_live_connection to 1." if not_stored(q["error"]) else ""
            )
            failures.append(f"{label} did not run: {q['error']}{hint}")
            continue
        print(f"{label}: {q.get('rows')} rows, {len(q.get('columns') or [])} columns")
        if not q.get("rows"):
            print("  zero rows -- say so to the user. Only they know whether that is wrong.")
    for c in result.get("charts", []):
        label = f"chart {c['name']} ({c.get('title')})"
        if c.get("errors"):
            failures.append(f"{label} failed: {c['errors']}")
            continue
        print(f"{label}: {c.get('rows')} rows")
        if unresolved := c.get("unresolved_order_by"):
            sort_dropped(label, unresolved, not c.get("ok"), failures)
    for d in result.get("dashboards", []):
        label = f"dashboard {d['name']} ({d.get('title')})"
        failures += [f"{label}: {error}" for error in d.get("errors") or []]
        for c in d.get("charts") or []:
            if not c.get("ok"):
                failures.append(f"{label} chart {c['name']} under {c.get('filters')}: {c.get('errors')}")
    if not failures and result.get("ok") is False:
        failures.append("verify_workbook answered ok: false")
    return finish(failures)


def unresolved_sorts(config, columns):
    """The `order_by` names of a chart config that the chart's result `columns` lack."""
    names = {column["name"] for column in columns}
    sorts = [(sort.get("column") or {}).get("column_name") for sort in config.get("order_by") or []]
    return [name for name in sorts if name and name not in names]


def sort_dropped(label, names, limited, failures):
    """A sort the chart's result has no column for, which the chart drops. With a
    `limit` the chart keeps other rows, so that fails; otherwise it is a warning."""
    message = f"{label} sorts by {names}, which its result does not have, so the sort is dropped"
    if limited:
        failures.append(f"{message}, and its limit keeps other rows")
    else:
        print(f"  warning: {message}")


def finish(failures):
    if failures:
        print("\nFAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK")
    return 0


def read_config(config):
    """The column names a chart config reads from its base query: dimensions,
    measures and chart filters. Skips the literal "count" of a row-count measure. An
    expression measure names no column, so it drops out on its own. `order_by` names
    are post-aggregation names, so they are not read from the query.
    """
    source = set()

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("column_name"), str):
                source.add(node["column_name"])
            for key, value in node.items():
                if key != "order_by":
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(config)
    source.discard("count")
    return source


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
        pending.extend(query_sources(operations_by_query[current]))
    return chain


def verify_locally():
    failures = []
    query_columns = {}

    queries = list_docs(QUERY, ["title", "operations", "use_live_connection"])
    charts = list_docs(CHART, ["title", "query", "chart_type", "config"])
    dashboards = list_docs(DASHBOARD, ["title", "items"])

    stored = {
        (t["data_source"], t["table_name"])
        for t in (
            call("method", "call", "insights.api.data_store.get_data_store_tables", "-F", "limit=1000") or []
        )
    }
    operations_by_query = {q["name"]: q["operations"] for q in queries}

    # Check 1 -- every query builds and runs.
    for q in queries:
        label = f"query {q['name']} ({q.get('title')})"
        operations = operations_by_query[q["name"]]
        if not operations:
            continue
        try:
            result = execute(q["name"])
        except CallFailed as e:
            failures.append(f"{label} did not run: {e}")
            continue
        query_columns[q["name"]] = {c["name"] for c in result["columns"]}
        rows = len(result["rows"])
        print(f"{label}: {rows} rows, {len(query_columns[q['name']])} columns")
        if rows:
            continue

        # Zero rows is a real answer on a live query. On a data store query it is not,
        # when a table is still importing: get_ibis_table hands back an empty table with
        # the right schema rather than an error, so the query "succeeds" and reads empty.
        unstored = sorted(t for t in source_tables(operations) if t not in stored)
        if not q.get("use_live_connection") and unstored:
            failures.append(
                f"{label} read zero rows from the data store, and {unstored} is not stored yet. The "
                "import is queued -- verify again when it finishes, or set use_live_connection to 1."
            )
        else:
            print("  zero rows -- say so to the user. Only they know whether that is wrong.")

    # Check 2 -- every chart runs. Saving does not validate a config, so a broken one
    # fails only here.
    for c in charts:
        label = f"chart {c['name']} ({c.get('title')})"
        try:
            result = run_chart(c["name"])
            if result.get("errors"):
                failures.append(f"{label} is not configured: {result['errors']}")
            else:
                print(f"{label}: {len(result['rows'])} rows")
                config = c.get("config") or {}
                if unresolved := unresolved_sorts(config, result["columns"]):
                    sort_dropped(label, unresolved, bool(config.get("limit")), failures)
        except CallFailed as e:
            failures.append(f"{label} did not run: {e}")
            # The usual cause is a column the base query does not have.
            cols = query_columns.get(c.get("query"))
            missing = sorted(read_config(c["config"]) - cols) if cols is not None else []
            if missing:
                failures.append(
                    f"{label} names columns its query does not have: {missing}. The query has: {sorted(cols)}"
                )

    # Check 3 -- every dashboard reference resolves.
    chart_base_query = {c["name"]: c.get("query") for c in charts}
    chart_names = set(chart_base_query)
    for d in dashboards:
        for item in d["items"]:
            if item.get("type") == "text" and not (item.get("text") or "").lstrip().startswith("<"):
                # The dashboard renders a text item as HTML, so markdown shows its marks.
                print(f"  note: dashboard {d['name']} has a text item that is not HTML: {item.get('text')!r}")

            # The grid reads item.layout.y and item.layout.h for every item, so one item
            # without a layout breaks the whole dashboard, not just itself.
            layout = item.get("layout")
            if not isinstance(layout, dict) or not layout.get("i"):
                failures.append(
                    f"dashboard {d['name']} has an item with no layout.i: {item.get('type')} "
                    f"{item.get('chart') or item.get('filter_name')!r}"
                )

            if item.get("type") == "chart" and item.get("chart") not in chart_names:
                failures.append(
                    f"dashboard {d['name']} points at chart {item.get('chart')!r}, which is not in this workbook"
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

    return finish(failures)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", help="the frappectl profile (default: $SITE)")
    parser.add_argument("--workbook", help="the target workbook name (default: $WORKBOOK)")
    parser.add_argument("--verify", action="store_true", help="skip the build")
    parser.add_argument(
        "--redesign",
        action="store_true",
        help="replace dashboard items whole, where the user has not changed them since the last run",
    )
    args = parser.parse_args()

    try:
        configure(args.site, args.workbook)
        if not args.verify:
            b = Build(redesign=args.redesign)
            build(b)
            if b.kept:
                print(f"\n{len(b.kept)} field(s) kept as the user edited them. Tell the user which.")
        return verify()
    except CallFailed as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
