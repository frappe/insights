# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Replay the slowest logged data store queries and report what each one cost.

Each replay runs `EXPLAIN ANALYZE` on its own read-only warehouse connection, and
samples `duckdb_memory()` while the query is in flight. A snapshot taken after
the query returns shows what was left over, not what the peak was made of.

From the bench:

    bench --site <site> execute insights.warehouse_profile.run --kwargs "{'limit': 10}"

`concurrency` replays a statement N times at once, as a dashboard does.
`insights.api.data_store.profile_warehouse` queues the same run as a job. Either
way the report is a private File.
"""

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from typing import Any

import frappe

import insights

# The settings that decide how much of the host one query may take. Insights sets
# `memory_limit` and leaves the rest at DuckDB's defaults, so a report that does
# not carry them cannot be read months later or compared across hosts.
PROFILED_SETTINGS = (
    "threads",
    "external_threads",
    "memory_limit",
    "max_memory",
    "temp_directory",
    "max_temp_directory_size",
    "preserve_insertion_order",
)

# How often the sampler asks DuckDB what it is holding. Fast enough to catch a
# hash table being built, cheap enough not to show up in the measurement.
SAMPLE_INTERVAL = 0.05

# A replayed query is cancelled past this, so profiling production cannot become
# the outage it is meant to explain.
DEFAULT_MAX_SECONDS = 180


def run(
    limit: int = 10,
    since_days: int = 7,
    min_time: float = 1.0,
    concurrency: int = 1,
    max_seconds: int = DEFAULT_MAX_SECONDS,
    file_name: str | None = None,
) -> str:
    """Profile the slowest logged data store queries and save the report as a private File.

    Args:
        limit: How many of the slowest distinct queries to replay.
        since_days: How far back to read the execution log.
        min_time: Ignore anything that already runs faster than this, in seconds.
        concurrency: Replay each statement this many times at once.
        max_seconds: Cancel a replay that runs longer than this.
        file_name: The report's file name. `enqueue` picks it, to answer with it.

    Returns:
        The name of the File that holds the report.
    """
    db = insights.warehouse.get_connection()
    try:
        settings = read_settings(db.con)
    finally:
        db.disconnect()

    report = {
        "generated_at": frappe.utils.now(),
        "site": frappe.local.site,
        "settings": settings,
        "concurrency": concurrency,
        "queries": [
            _replay(query, concurrency, max_seconds) for query in slowest_logged(limit, since_days, min_time)
        ],
    }
    file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name or report_file_name(),
            "is_private": 1,
            "content": json.dumps(report, indent=2, default=str),
        }
    ).insert(ignore_permissions=True)
    print(summarize(report))
    print(f"\nFull report: {file.get_full_path()}")
    return file.name


def enqueue(
    limit: int = 10,
    since_days: int = 7,
    min_time: float = 1.0,
    concurrency: int = 1,
    max_seconds: int = DEFAULT_MAX_SECONDS,
) -> str:
    """Queue `run` on the long queue and answer with the file name its report will have."""
    file_name = report_file_name()
    frappe.enqueue(
        "insights.warehouse_profile.run",
        queue="long",
        # concurrent copies run side by side, so each query costs at most `max_seconds`
        timeout=limit * max_seconds + 60,
        limit=limit,
        since_days=since_days,
        min_time=min_time,
        concurrency=concurrency,
        max_seconds=max_seconds,
        file_name=file_name,
    )
    return file_name


def report_file_name() -> str:
    return (
        f"warehouse_profile_{frappe.utils.now_datetime():%Y%m%d_%H%M%S}_{frappe.generate_hash(length=6)}.json"
    )


def slowest_logged(limit: int, since_days: int, min_time: float) -> list[dict]:
    """The slowest logged data store queries, one row per distinct query."""
    return frappe.db.sql(
        """
        SELECT l.query, l.`sql`, l.time_taken
        FROM `tabInsights Query Execution Log` l
        JOIN (
            SELECT query, MAX(time_taken) AS worst
            FROM `tabInsights Query Execution Log`
            WHERE data_store = 1 AND query IS NOT NULL
                AND creation > NOW() - INTERVAL %(days)s DAY
            GROUP BY query
            HAVING worst >= %(min_time)s
            ORDER BY worst DESC
            LIMIT %(limit)s
        ) w ON w.query = l.query AND w.worst = l.time_taken
        GROUP BY l.query
        ORDER BY l.time_taken DESC
        """,
        {"days": since_days, "min_time": min_time, "limit": limit},
        as_dict=True,
    )


def read_settings(con) -> dict[str, Any]:
    """The DuckDB settings a warehouse connection runs under."""
    settings = {}
    for name in PROFILED_SETTINGS:
        with suppress(Exception):  # nosemgrep - a setting this build does not have is simply absent
            settings[name] = con.execute(f"SELECT current_setting('{name}')").fetchone()[0]
    settings["cpu_count"] = os.cpu_count()
    return settings


def sql_shape(sql: str) -> dict[str, int]:
    """How big and how nested the generated SQL is.

    A plan's cost starts with what the planner is handed. ibis inlines a lookup
    table as a chain of `UNION ALL` branches and repeats a subquery rather than
    naming it in a CTE, so these counts separate a query that reads a lot of rows
    from one that merely asks DuckDB to plan a lot of SQL.
    """
    depth = max_depth = 0
    for char in sql:
        if char == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == ")":
            depth -= 1

    return {
        "bytes": len(sql),
        "selects": len(re.findall(r"\bSELECT\b", sql, re.I)),
        "unions": len(re.findall(r"\bUNION\b", sql, re.I)),
        "joins": len(re.findall(r"\bJOIN\b", sql, re.I)),
        "ctes": len(re.findall(r"\bWITH\b", sql, re.I)),
        "scans": len(re.findall(r"\bFROM\s+\"", sql, re.I)),
        "max_nesting": max_depth,
    }


def memory_by_tag(con) -> dict[str, tuple[int, int]]:
    """What the DuckDB instance holds, per tag: memory and temporary storage, in bytes."""
    rows = con.execute(
        "SELECT tag, memory_usage_bytes, temporary_storage_bytes FROM duckdb_memory()"
    ).fetchall()
    return {tag: (memory, temporary) for tag, memory, temporary in rows}


class MemorySampler(threading.Thread):
    """Polls `duckdb_memory()` on a sibling cursor while a query runs.

    Sibling cursors share the buffer manager, so this reports the instance's
    usage, not the thread's. It keeps the highest total above `baseline` it sees,
    and the per-tag breakdown from that moment.
    """

    def __init__(self, con, baseline: dict[str, tuple[int, int]], interval: float = SAMPLE_INTERVAL):
        super().__init__(daemon=True)
        self.cursor = con.cursor()
        self.baseline = baseline
        self.interval = interval
        self.stop_event = threading.Event()
        self.peak_bytes = 0
        self.peak_by_tag: dict[str, int] = {}
        self.peak_temp_bytes = 0
        self.samples = 0

    def run(self) -> None:
        while not self.stop_event.is_set():
            with suppress(Exception):  # nosemgrep - a lost sample must not fail the query it watches
                self._sample()
            self.stop_event.wait(self.interval)

    def _sample(self) -> None:
        growth = {
            tag: (memory - self.baseline.get(tag, (0, 0))[0], temporary - self.baseline.get(tag, (0, 0))[1])
            for tag, (memory, temporary) in memory_by_tag(self.cursor).items()
        }
        self.samples += 1
        total = sum(memory for memory, _ in growth.values())
        if total <= self.peak_bytes:
            return
        self.peak_bytes = total
        self.peak_by_tag = {tag: memory for tag, (memory, _) in growth.items() if memory > 0}
        self.peak_temp_bytes = sum(temporary for _, temporary in growth.values())

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.join(timeout=5)
        self.cursor.close()
        return {
            "sampled_peak_bytes": self.peak_bytes,
            "sampled_peak_by_tag": self.peak_by_tag,
            "sampled_peak_temp_bytes": self.peak_temp_bytes,
            "samples": self.samples,
        }


def profile_sql(con, sql: str, baseline: dict, max_seconds: int = DEFAULT_MAX_SECONDS) -> dict[str, Any]:
    """Run one statement on `con` and report where its time and memory went.

    `EXPLAIN ANALYZE` runs the query for real and returns the plan with
    per-operator timings, without handing the rows back to Python, so what is
    measured is DuckDB's work, not pandas'. It reads the profile from its own
    result rather than `profiling_output`: asking a connection without external
    access to write a profile file makes DuckDB 1.4 dereference a null pointer.

    Args:
        con: A warehouse connection of this replay's own.
        sql: The statement to replay.
        baseline: `memory_by_tag` before the replay, which the memory peak is above.
        max_seconds: Cancel the query once it has run this long.
    """
    con.execute("SET enable_profiling = 'json'")
    con.execute("SET profiling_mode = 'standard'")
    sampler = MemorySampler(con, baseline)
    watchdog = threading.Timer(max_seconds, con.interrupt)
    watchdog.daemon = True
    profile, error = None, None

    sampler.start()
    watchdog.start()
    started = time.monotonic()
    try:
        rows = con.execute(f"EXPLAIN ANALYZE {sql.strip().rstrip(';')}").fetchall()
        profile = json.loads(rows[0][-1])
    except Exception as e:
        error = str(e).splitlines()[0][:500]
    finally:
        watchdog.cancel()
    wall = round(time.monotonic() - started, 3)

    return {"wall_seconds": wall, "error": error, **sampler.stop(), **_read_profile(profile)}


def _read_profile(profile: dict | None) -> dict[str, Any]:
    """The costliest operators, and the work the plan did as a whole.

    `EXPLAIN ANALYZE` leaves the root counters (`latency`, `cpu_time`,
    `system_peak_buffer_memory`) at zero — they are only filled in when the
    profile is written out to a file, which this connection cannot do. So the
    time here is summed from the operators and the memory comes from the
    sampler, not from DuckDB's own summary.
    """
    if not profile:
        return {"operators": 0, "operator_seconds": 0, "rows_scanned": 0, "top_operators": []}

    operators: list[dict] = []
    _collect_operators(profile, operators)
    operators.sort(key=lambda op: op["seconds"], reverse=True)
    return {
        "operators": len(operators),
        "operator_seconds": round(sum(op["seconds"] for op in operators), 3),
        "rows_scanned": sum(op["rows_scanned"] or 0 for op in operators),
        "top_operators": operators[:12],
    }


def _collect_operators(node: dict, into: list[dict]) -> None:
    """Flatten the plan tree into one row per operator."""
    name = node.get("operator_name") or node.get("operator_type")
    if name:
        into.append(
            {
                "operator": name,
                "seconds": round(node.get("operator_timing") or 0, 4),
                "rows_out": node.get("operator_cardinality"),
                "rows_scanned": node.get("operator_rows_scanned"),
                "detail": _operator_detail(node),
            }
        )
    for child in node.get("children") or []:
        _collect_operators(child, into)


def _operator_detail(node: dict) -> str:
    """The one line of `extra_info` worth keeping — usually the table or the keys."""
    info = node.get("extra_info")
    if not isinstance(info, dict):
        return ""
    for key in ("Table", "Text", "Join Type", "Groups", "Projections"):
        if value := info.get(key):
            value = value[0] if isinstance(value, list) and value else value
            return f"{key}: {str(value)[:120]}"
    return ""


def _replay(logged: dict, concurrency: int, max_seconds: int) -> dict[str, Any]:
    """Profile one logged statement, alone or against copies of itself.

    Each copy runs on a connection of its own, opened through the warehouse so
    it has the settings a dashboard query has, and closed after so that the
    next replay starts on an empty buffer and writers can open the file between
    replays. A worker thread has no `frappe.local`, so the connections are opened
    here.
    """
    entry = {
        "query": logged["query"],
        "logged_seconds": logged["time_taken"],
        "shape": sql_shape(logged["sql"]),
    }
    dbs = [insights.warehouse.get_connection() for _ in range(concurrency)]
    try:
        baseline = memory_by_tag(dbs[0].con)
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            entry["runs"] = list(
                pool.map(lambda db: profile_sql(db.con, logged["sql"], baseline, max_seconds), dbs)
            )
    finally:
        for db in dbs:
            db.disconnect()
    return entry


def summarize(report: dict) -> str:
    """A table of the report, for reading in a terminal."""
    lines = [
        f"DuckDB settings: {report['settings']}",
        "",
        (  # nosemgrep - one header line, split to fit
            f"{'query':<22}{'logged':>8}{'wall':>8}{'optime':>8}{'peakRAM':>10}{'spill':>9}"
            f"{'ops':>6}{'SQL kB':>8}{'unions':>8}"
        ),
        "-" * 90,
    ]
    for entry in report["queries"]:
        lines.append(_summary_row(entry))
    return "\n".join(lines)


def _summary_row(entry: dict) -> str:
    """One line per query: what it cost alone, or at the chosen concurrency."""
    runs = entry["runs"]
    wall = max(r["wall_seconds"] for r in runs)
    peak = max(r["sampled_peak_bytes"] for r in runs)
    spill = max(r["sampled_peak_temp_bytes"] for r in runs)
    optime = sum(r["operator_seconds"] for r in runs)
    shape = entry["shape"]
    return (
        f"{entry['query']:<22}{entry['logged_seconds']:>8.1f}{wall:>8.1f}{optime:>8.1f}"
        f"{peak / 1e6:>9.0f}M{spill / 1e6:>8.0f}M{runs[0]['operators']:>6}"
        f"{shape['bytes'] / 1024:>8.0f}{shape['unions']:>8}"
    )
