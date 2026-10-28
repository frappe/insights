# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Read the recorder's events back into what happened, and why.

Starts are paired with their ends. A start with no end is sorted by what its
process did next: a process that kept writing events lost only this end; one
that never wrote again and is gone was killed with the work in hand, by the
request timeout or by the kernel.
"""

import time
from collections import defaultdict
from statistics import median
from typing import Any

import psutil

from insights.profiler import events

PAIRED = ("request", "query", "job")
TOP = 50


def summarize(
    since: float, until: float, dashboard: str | None = None, chart: str | None = None
) -> dict[str, Any]:
    """Everything recorded between two epoch times, optionally for one dashboard or chart."""
    found = list(events.read(since, until + 3600))  # ends of work started inside the window
    records = _pair(found, since, until)
    if dashboard or chart:
        records = [r for r in records if _belongs(r, dashboard, chart)]
    queries = [r for r in records if r["kind"] == "query"]
    requests = [r for r in records if r["kind"] == "request"]
    return {
        "window": {"since": since, "until": until, "events": len(found)},
        "requests": _requests(requests),
        "queries": _queries(queries),
        "connections": _connections(found, since, until),
        "jobs": [r for r in records if r["kind"] == "job"][:TOP],
        "timeline": timeline(queries, requests, until),
        "by_dashboard": _by(queries, "dashboard"),
        "by_chart": _by(queries, "chart"),
        "statements": _statements(queries),
        "failures": _failures(records),
    }


# --- pairing ------------------------------------------------------------------


def _pair(found: list[dict], since: float, until: float) -> list[dict]:
    ends = {e["id"]: e for e in found if e["kind"].endswith(".end")}
    last_seen = _last_event_by_process(found)
    records = []
    for start in found:
        if start["kind"] not in PAIRED or not since <= start["ts"] <= until:
            continue
        end = ends.get(start["id"])
        record = {**start, **(end or {}), "kind": start["kind"], "ts": start["ts"]}
        record["state"] = _state(start, end, last_seen)
        records.append(record)
    return records


def _last_event_by_process(found: list[dict]) -> dict[tuple, float]:
    last: dict[tuple, float] = {}
    for e in found:
        if "pid" in e:
            key = (e["pid"], e.get("pid_started"))
            last[key] = max(last.get(key, 0), e["ts"])
    return last


def _state(start: dict, end: dict | None, last_seen: dict[tuple, float]) -> str:
    """ok, failed, or — with no end — what became of the process."""
    if end is not None:
        if start["kind"] == "request":
            return "ok" if (end.get("status") or 500) < 400 else "failed"
        return "ok" if end.get("ok", True) else "failed"
    process = (start["pid"], start.get("pid_started"))
    if last_seen.get(process, 0) > start["ts"]:
        return "end not recorded"
    return "running" if _alive(*process) else "killed"


def _alive(pid: int, started: float | None) -> bool:
    try:
        proc = psutil.Process(pid)
        return started is None or abs(proc.create_time() - started) < 1
    except psutil.Error:
        return False  # nosemgrep - a pid this process cannot see is not a live worker


def _belongs(record: dict, dashboard: str | None, chart: str | None) -> bool:
    if dashboard and record.get("dashboard") != dashboard:
        return False
    return not chart or chart in (record.get("chart"), record.get("chart_name"))


# --- sections -----------------------------------------------------------------


def _requests(requests: list[dict]) -> dict[str, Any]:
    by_status: dict[str, int] = defaultdict(int)
    by_path: dict[str, list[float]] = defaultdict(list)
    for r in requests:
        by_status[str(r.get("status") or r["state"])] += 1
        if r.get("duration") is not None:
            by_path[r["path"]].append(r["duration"])
    return {
        "count": len(requests),
        "by_status": dict(by_status),
        "by_endpoint": {
            path: _spread(d) for path, d in sorted(by_path.items(), key=lambda x: -sum(x[1]))[:TOP]
        },
    }


def _queries(queries: list[dict]) -> dict[str, Any]:
    by_state: dict[str, int] = defaultdict(int)
    by_cache: dict[str, int] = defaultdict(int)
    for q in queries:
        by_state[q["state"] if q["state"] != "failed" else f"failed: {q.get('error_type')}"] += 1
        by_cache[q.get("cache") or "unknown"] += 1
    ran = [q for q in queries if q.get("cache") != "hit"]
    return {
        "count": len(queries),
        "by_state": dict(by_state),
        "by_cache": dict(by_cache),
        "duplicates_in_flight": sum(_duplicates_in_flight(ran).values()),
        "duration": _spread([q["duration"] for q in ran if q.get("duration") is not None]),
        "cpu_s": round(sum(q.get("cpu_s") or 0 for q in ran), 1),
    }


def _duplicates_in_flight(ran: list[dict]) -> dict[str, int]:
    """Per statement, runs that started while an identical one was still running.

    Each one is work the result cache could not save: it is filled only when a
    run finishes.
    """
    by_sql: dict[str, list[dict]] = defaultdict(list)
    for q in ran:
        by_sql[q["sql"]].append(q)
    found = {}
    for digest, runs in by_sql.items():
        runs.sort(key=lambda q: q["ts"])
        count = sum(1 for i, q in enumerate(runs) if any(_overlaps(p, q["ts"]) for p in runs[:i]))
        if count:
            found[digest] = count
    return found


def _overlaps(earlier: dict, ts: float) -> bool:
    return earlier["ts"] <= ts <= earlier["ts"] + (earlier.get("duration") or 0)


def _connections(found: list[dict], since: float, until: float) -> dict[str, Any]:
    opens = [e for e in found if e["kind"] == "connect" and since <= e["ts"] <= until]
    refused = [e for e in opens if not e.get("ok")]
    return {
        "count": len(opens),
        "refused": len(refused),
        "refused_by_lock": sum(1 for e in refused if e.get("lock")),
        "wait": _spread([e.get("duration") or 0 for e in opens]),
        "refusals": refused[:TOP],
    }


def _by(queries: list[dict], field: str) -> list[dict]:
    """Queries grouped by the dashboard or chart their request named."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for q in queries:
        groups[q.get(field) or q.get(f"{field}_name") or "(none)"].append(q)
    rows = [_group(name, runs) for name, runs in groups.items()]
    return sorted(rows, key=lambda r: r["seconds"], reverse=True)[:TOP]


def _group(name: str, runs: list[dict]) -> dict[str, Any]:
    ran = [q for q in runs if q.get("cache") != "hit"]
    return {
        "name": name,
        "runs": len(runs),
        "cache_hits": len(runs) - len(ran),
        "failed": sum(1 for q in runs if q["state"] == "failed"),
        "killed": sum(1 for q in runs if q["state"] == "killed"),
        "seconds": round(sum(q.get("duration") or 0 for q in ran), 1),
        "duration": _spread([q["duration"] for q in ran if q.get("duration") is not None]),
    }


def _statements(queries: list[dict]) -> list[dict]:
    """The statements that cost the most, by total time across their runs."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for q in queries:
        if q.get("cache") != "hit":
            groups[q["sql"]].append(q)
    duplicates = _duplicates_in_flight([q for runs in groups.values() for q in runs])
    rows = [
        {
            **_group(digest, runs),
            "digest": digest,
            "sql_bytes": runs[0].get("sql_bytes"),
            "duplicates": duplicates.get(digest, 0),
        }
        for digest, runs in groups.items()
    ]
    return sorted(rows, key=lambda r: r["seconds"], reverse=True)[:TOP]


def _failures(records: list[dict]) -> list[dict]:
    failed = [r for r in records if r["state"] in ("failed", "killed")]
    keep = (
        "kind",
        "ts",
        "state",
        "status",
        "error_type",
        "error",
        "path",
        "dashboard",
        "chart",
        "chart_name",
        "sql",
        "duration",
        "pid",
        "user",
    )
    return [
        {k: r.get(k) for k in keep if r.get(k) is not None}
        for r in sorted(failed, key=lambda r: -r["ts"])[:TOP]
    ]


# --- over time ----------------------------------------------------------------


def timeline(queries: list[dict], requests: list[dict], until: float) -> list[dict]:
    """Per minute: data store queries running at once, and requests that failed."""
    intervals = [
        _interval(q, until) for q in queries if q.get("source") == "data_store" and q.get("cache") != "hit"
    ]
    if not intervals:
        return []
    minutes = range(int(min(s for s, _ in intervals) // 60), int(max(e for _, e in intervals) // 60) + 1)
    return [_minute(m * 60, intervals, queries, requests) for m in minutes]


def _interval(q: dict, until: float) -> tuple[float, float]:
    end = q["ts"] + q["duration"] if q.get("duration") is not None else min(until, time.time())
    return q["ts"], end


def _minute(
    start: float, intervals: list[tuple[float, float]], queries: list[dict], requests: list[dict]
) -> dict:
    end = start + 60
    busy = sum(max(0.0, min(e, end) - max(s, start)) for s, e in intervals)
    return {
        "minute": start,
        "average_running": round(busy / 60, 2),
        "most_running": _most_at_once(intervals, start, end),
        "queries_started": sum(1 for q in queries if start <= q["ts"] < end),
        "queries_failed": sum(
            1 for q in queries if start <= q["ts"] < end and q["state"] in ("failed", "killed")
        ),
        "requests_failed": sum(
            1 for r in requests if start <= r["ts"] < end and r["state"] in ("failed", "killed")
        ),
        "max_rss": max((q.get("rss_end") or 0 for q in queries if start <= q["ts"] < end), default=0),
    }


def _most_at_once(intervals: list[tuple[float, float]], start: float, end: float) -> int:
    edges = sorted(
        [(max(s, start), 1) for s, e in intervals if s < end and e > start]
        + [(min(e, end), -1) for s, e in intervals if s < end and e > start]
    )
    running = most = 0
    for _, step in edges:
        running += step
        most = max(most, running)
    return most


def _spread(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    values = sorted(values)
    return {
        "median": round(median(values), 3),
        "p95": round(values[min(len(values) - 1, int(len(values) * 0.95))], 3),
        "max": round(values[-1], 3),
    }
