# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Replay the slowest logged data store queries and report what each one cost.

Each replay runs `EXPLAIN ANALYZE` on its own read-only warehouse connection, and
samples `duckdb_memory()` while the query is in flight. A snapshot taken after
the query returns shows what was left over, not what the peak was made of.

From the bench:

    bench --site <site> execute insights.warehouse_profile.run --kwargs "{'limit': 10}"

`concurrency` replays a statement N times at once, as a dashboard does. The
copies run in one process and share one DuckDB instance, its threads and its
memory limit, where web workers in separate processes each have their own.
`insights.api.data_store.profile_warehouse` queues the same run as a job. Either
way the report is a private File, rewritten after every replay.
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
from duckdb import IOException
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Max
from frappe.utils import add_days, now_datetime
from frappe.utils.background_jobs import is_job_enqueued
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

import insights
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import WRITE_LOCK_RETRY_INTERVAL

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

# Two profiles at once would each measure the other's load.
PROFILE_LOCK = "insights_warehouse_profile"

# A replay holds the file for reading, and a writer waiting for it retries this
# often. A pause longer than that between replays lets the writer in.
WRITER_PAUSE = 2 * WRITE_LOCK_RETRY_INTERVAL


def run(
    limit: int = 10,
    since_days: int = 7,
    min_time: float = 1.0,
    concurrency: int = 1,
    max_seconds: int = DEFAULT_MAX_SECONDS,
    file: str | None = None,
) -> str:
    """Profile the slowest logged data store queries into a private File.

    The report is rewritten after every replay, so a run that is killed still
    leaves what it measured. Its `status` then stays `Running`, and its
    `updated_at` stops moving.

    Args:
        limit: How many of the slowest distinct queries to replay.
        since_days: How far back to read the execution log.
        min_time: Ignore anything that already runs faster than this, in seconds.
        concurrency: Replay each statement this many times at once.
        max_seconds: Cancel a replay that runs longer than this, and give up
            waiting for a writer to release the file after as long.
        file: The name of the File to write the report to. `enqueue` creates it,
            to answer with it.

    Returns:
        The name of the File that holds the report.
    """
    file = frappe.get_doc("File", file) if file else create_report_file()
    report = {
        "generated_at": frappe.utils.now(),
        "site": frappe.local.site,
        "concurrency": concurrency,
        "status": "Running",
        "error": None,
        "queries": [],
    }
    write_report(file, report)
    try:
        with filelock(PROFILE_LOCK, timeout=0):
            for query in slowest_logged(limit, since_days, min_time):
                report["queries"].append(_replay(query, concurrency, max_seconds))
                write_report(file, report)
        report["status"] = "Done"
    except LockTimeoutError:
        report["status"] = "Failed"
        report["error"] = "Another warehouse profile is running"
    except Exception as e:
        frappe.log_error(title="Warehouse profile failed")
        report["status"] = "Failed"
        report["error"] = str(e).splitlines()[0][:500] if str(e) else type(e).__name__

    write_report(file, report)
    print(summarize(report))
    print(f"\nFull report: File {file.name}, {file.file_url}")
    return file.name


def enqueue(
    limit: int = 10,
    since_days: int = 7,
    min_time: float = 1.0,
    concurrency: int = 1,
    max_seconds: int = DEFAULT_MAX_SECONDS,
) -> str:
    """Queue `run` on the long queue, one profile at a time.

    Returns:
        The name of the private File the job writes its report to. Its
        `status` is `Queued` until the job starts.
    """
    if not slowest_logged(limit, since_days, min_time):
        frappe.throw(
            _("No data store queries slower than {0}s in the last {1} days").format(min_time, since_days)
        )

    # two requests at once would both find no job queued
    with filelock(f"{PROFILE_LOCK}_enqueue", timeout=5):
        if is_job_enqueued(PROFILE_LOCK):
            frappe.throw(_("A warehouse profile is already queued or running"))
        file = create_report_file()
        frappe.db.commit()  # nosemgrep - the job reads the File, and the next request must see the job
        frappe.enqueue(
            "insights.warehouse_profile.run",
            queue="long",
            job_id=PROFILE_LOCK,
            # a replay waits up to `max_seconds` for a writer, then runs up to as long;
            # concurrent copies run side by side
            timeout=limit * (2 * max_seconds + WRITER_PAUSE) + 60,
            limit=limit,
            since_days=since_days,
            min_time=min_time,
            concurrency=concurrency,
            max_seconds=max_seconds,
            file=file.name,
        )
    return file.name


def create_report_file():
    return frappe.get_doc(
        {
            "doctype": "File",
            "file_name": f"warehouse_profile_{now_datetime():%Y%m%d_%H%M%S}.json",
            "is_private": 1,
            # File shares one stored copy among equal contents, so the first must be unique
            "content": json.dumps({"status": "Queued", "queued_at": frappe.utils.now()}),
        }
    ).insert(ignore_permissions=True)


def write_report(file, report: dict) -> None:
    report["updated_at"] = frappe.utils.now()
    file.save_file(content=json.dumps(report, indent=2, default=str), overwrite=True)
    file.save(ignore_permissions=True)
    frappe.db.commit()  # nosemgrep - a killed job must leave the report as far as it got


def slowest_logged(limit: int, since_days: int, min_time: float) -> list[dict]:
    """The slowest logged data store queries, one row per distinct query, slowest first."""
    Log = frappe.qb.DocType("Insights Query Execution Log")
    worst = Max(Log.time_taken)
    slowest = (
        frappe.qb.from_(Log)
        .select(Log.query, worst.as_("time_taken"))
        .where(
            (Log.data_store == 1)
            & Log.query.isnotnull()
            & (Log.creation > add_days(now_datetime(), -since_days))
        )
        .groupby(Log.query)
        .having(worst >= min_time)
        .orderby(worst, order=Order.desc)
        .limit(limit)
        .run(as_dict=True)
    )
    for row in slowest:
        row["sql"] = frappe.db.get_value(
            "Insights Query Execution Log", {"query": row.query, "time_taken": row.time_taken}, "sql"
        )
    return slowest


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
        total = sum(memory for memory, temporary in growth.values())
        if total <= self.peak_bytes:
            return
        self.peak_bytes = total
        self.peak_by_tag = {tag: memory for tag, (memory, temporary) in growth.items() if memory > 0}
        self.peak_temp_bytes = sum(temporary for memory, temporary in growth.values())

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
    it has the warehouse's settings, and closed after so that the next replay
    starts on an empty buffer. A worker thread has no `frappe.local`, so the
    connections are opened here.
    """
    entry = {
        "query": logged["query"],
        "logged_seconds": logged["time_taken"],
        "shape": sql_shape(logged["sql"]),
        "error": None,
        "runs": [],
    }
    dbs = []
    deadline = time.monotonic() + max_seconds
    try:
        while len(dbs) < concurrency:
            dbs.append(_open_warehouse(deadline))
        entry["settings"] = read_settings(dbs[0].con)
        baseline = memory_by_tag(dbs[0].con)
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            entry["runs"] = list(
                pool.map(lambda db: profile_sql(db.con, logged["sql"], baseline, max_seconds), dbs)
            )
    except IOException as e:  # a writer held the file past the deadline
        entry["error"] = str(e).splitlines()[0][:500]
    finally:
        for db in dbs:
            db.disconnect()
        time.sleep(WRITER_PAUSE)
    return entry


def _open_warehouse(deadline: float):
    """Open the warehouse read-only, waiting out a writer, as an import's commit, until `deadline`."""
    while True:
        try:
            return insights.warehouse.get_connection()
        except IOException as e:
            if "Could not set lock" not in str(e) or time.monotonic() >= deadline:
                raise
            time.sleep(WRITE_LOCK_RETRY_INTERVAL)


def summarize(report: dict) -> str:
    """A table of the report, for reading in a terminal."""
    lines = [
        f"DuckDB settings: {next((e['settings'] for e in report['queries'] if 'settings' in e), {})}",
        "",
        (  # nosemgrep - one header line, split to fit
            f"{'query':<22}{'logged':>8}{'wall':>8}{'optime':>8}{'peakRAM':>10}{'spill':>9}"
            f"{'ops':>6}{'SQL kB':>8}{'unions':>8}"
        ),
        "-" * 90,
    ]
    for entry in report["queries"]:
        lines.append(_summary_row(entry))
    if report["error"]:
        lines.append(f"Stopped: {report['error']}")
    return "\n".join(lines)


def _summary_row(entry: dict) -> str:
    """One line per query: what it cost alone, or at the chosen concurrency."""
    runs = entry["runs"]
    if not runs:
        return f"{entry['query']:<22}{entry['logged_seconds']:>8.1f}  {entry['error']}"
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
