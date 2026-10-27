# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Profile what the warehouse's DuckDB actually spends on a query.

Replays SQL that already ran — taken from `Insights Query Execution Log` — against
the warehouse read-only, one query at a time, and records where the time and the
memory went:

- DuckDB's own profile tree, with per-operator timing and cardinality
- `system_peak_buffer_memory` and `system_peak_temp_dir_size` for the run
- `duckdb_memory()` sampled *while the query is in flight*, which is the only way
  to see which operator held the memory. A snapshot taken after the query has
  returned shows what was left over, not what the peak was made of
- `cpu_time` against `latency`, whose ratio is how many cores the query took

Nothing here is whitelisted: it reads arbitrary logged SQL and reports plans, so
it is an operator's tool, run from the bench root, off-peak:

    bench --site insights.frappe.io execute \\
        insights.warehouse_profile.run --kwargs "{'limit': 10}"

`concurrency` replays the same statement N times at once, which is what a
dashboard does to the warehouse and what a one-at-a-time profile cannot show:

    bench --site insights.frappe.io execute \\
        insights.warehouse_profile.run --kwargs "{'limit': 3, 'concurrency': 4}"

Each run writes a JSON report to the site's private files and prints a summary.
"""

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from typing import Any

import frappe
from frappe.utils import get_files_path

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
    out: str | None = None,
) -> str:
    """Profile the slowest logged warehouse queries and write a JSON report.

    Args:
        limit: How many of the slowest distinct queries to replay.
        since_days: How far back to read the execution log.
        min_time: Ignore anything that already runs faster than this, in seconds.
        concurrency: Replay each statement this many times at once.
        max_seconds: Cancel a replay that runs longer than this.
        out: Path to write the report to. Defaults to the site's private files.

    Returns:
        The path the report was written to.
    """
    queries = slowest_logged(limit, since_days, min_time)
    if not queries:
        frappe.throw(f"No data store queries slower than {min_time}s in the last {since_days} days")

    report = {
        "generated_at": frappe.utils.now(),
        "site": frappe.local.site,
        "settings": read_settings(),
        "concurrency": concurrency,
        "queries": [_replay(q, concurrency, max_seconds) for q in queries],
    }
    path = _write_report(report, out)
    print(summarize(report))
    print(f"\nFull report: {path}")
    return path


def slowest_logged(limit: int, since_days: int, min_time: float) -> list[dict]:
    """The slowest logged data store queries, one row per distinct query."""
    return frappe.db.sql(
        """
        SELECT l.query, l.`sql`, l.time_taken
        FROM `tabInsights Query Execution Log` l
        JOIN (
            SELECT query, MAX(time_taken) AS worst
            FROM `tabInsights Query Execution Log`
            WHERE data_store = 1 AND creation > NOW() - INTERVAL %(days)s DAY
            GROUP BY query
            HAVING worst >= %(min_time)s
            ORDER BY worst DESC
            LIMIT %(limit)s
        ) w ON w.query = l.query AND w.worst = l.time_taken
        GROUP BY l.query
        """,
        {"days": since_days, "min_time": min_time, "limit": limit},
        as_dict=True,
    )


def read_settings() -> dict[str, Any]:
    """The DuckDB settings this warehouse connection actually runs under."""
    con = insights.warehouse.db.con
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


class MemorySampler(threading.Thread):
    """Polls `duckdb_memory()` on a sibling cursor while a query runs.

    Sibling cursors share the buffer manager with the connection they came from,
    so this reports the instance's usage, not the thread's. It keeps the single
    highest total it sees and the per-tag breakdown from that moment.
    """

    def __init__(self, con, interval: float = SAMPLE_INTERVAL):
        super().__init__(daemon=True)
        self.cursor = con.cursor()
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
        rows = self.cursor.execute(
            "SELECT tag, memory_usage_bytes, temporary_storage_bytes FROM duckdb_memory()"
        ).fetchall()
        self.samples += 1
        total = sum(row[1] for row in rows)
        if total <= self.peak_bytes:
            return
        self.peak_bytes = total
        self.peak_by_tag = {row[0]: row[1] for row in rows if row[1]}
        self.peak_temp_bytes = sum(row[2] for row in rows)

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.join(timeout=5)
        return {
            "sampled_peak_bytes": self.peak_bytes,
            "sampled_peak_by_tag": self.peak_by_tag,
            "sampled_peak_temp_bytes": self.peak_temp_bytes,
            "samples": self.samples,
        }


@contextmanager
def profiling(con):
    """Turn DuckDB's JSON profiler on for the block, and off again after.

    The profile is read back from `EXPLAIN ANALYZE`'s own result rather than
    `profiling_output`. The warehouse opens read-only with
    `enable_external_access = false`, and asking that connection to write a
    profile file does not fail cleanly — DuckDB 1.4 dereferences a null pointer
    and takes the query with it.
    """
    try:
        con.execute("SET enable_profiling='json'")
        con.execute("SET profiling_mode='standard'")
        yield
    finally:
        with suppress(
            Exception
        ):  # nosemgrep - the connection is shared; leaving it profiling is the real risk
            con.execute("PRAGMA disable_profiling")


def profile_sql(
    sql: str,
    max_seconds: int = DEFAULT_MAX_SECONDS,
    connection=None,
) -> dict[str, Any]:
    """Run one statement read-only and report where its time and memory went.

    `EXPLAIN ANALYZE` runs the query for real and returns the plan with
    per-operator timings, without handing the rows back to Python — so what is
    measured is DuckDB's work, not pandas'.

    Args:
        sql: The statement to replay.
        max_seconds: Cancel the query once it has run this long.
        connection: The warehouse connection to open a cursor on. A concurrent
            replay must pass one: `insights.warehouse` reads `frappe.local`,
            which is thread-local and empty in a worker thread.
    """
    con = (connection or insights.warehouse.db.con).cursor()
    sampler = MemorySampler(con)
    watchdog = _interrupt_after(con, max_seconds)
    profile, error = None, None

    with profiling(con):
        sampler.start()
        started = time.monotonic()
        try:
            rows = con.execute(f"EXPLAIN ANALYZE {sql.strip().rstrip(';')}").fetchall()
            profile = json.loads(rows[0][-1])
        except Exception as e:
            error = str(e).splitlines()[0][:500]
        wall = round(time.monotonic() - started, 3)

    watchdog.cancel()
    return {"wall_seconds": wall, "error": error, **sampler.stop(), **_read_profile(profile)}


def _interrupt_after(con, seconds: int) -> threading.Timer:
    """Cancel the query on this connection once it has had long enough."""
    timer = threading.Timer(seconds, con.interrupt)
    timer.daemon = True
    timer.start()
    return timer


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
    """Profile one logged statement, alone or against copies of itself."""
    entry = {
        "query": logged["query"],
        "logged_seconds": logged["time_taken"],
        "shape": sql_shape(logged["sql"]),
    }
    connection = insights.warehouse.db.con
    if concurrency <= 1:
        entry["runs"] = [profile_sql(logged["sql"], max_seconds, connection)]
        return entry

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(profile_sql, logged["sql"], max_seconds, connection) for _ in range(concurrency)
        ]
        entry["runs"] = [f.result() for f in futures]
    return entry


def _write_report(report: dict, out: str | None) -> str:
    path = out or os.path.join(
        get_files_path(is_private=1), f"warehouse_profile_{frappe.utils.now_datetime():%Y%m%d_%H%M%S}.json"
    )
    path = os.path.abspath(path)
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def summarize(report: dict) -> str:
    """A table of the report, for reading in a terminal."""
    lines = [
        f"DuckDB settings: {report['settings']}",
        "",
        f"{'query':<22}{'logged':>8}{'wall':>8}{'optime':>8}{'peakRAM':>10}{'spill':>9}"
        f"{'ops':>6}{'SQL kB':>8}{'unions':>8}",
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
