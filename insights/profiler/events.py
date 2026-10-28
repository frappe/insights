# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Where the recorder's events live, and the switch that turns it on.

Events go to append-only JSON-lines files, one per UTC day, not to the
database. A request that fails rolls its transaction back, and a worker that is
killed never commits, and those are exactly the events this exists to keep. A
line is written the moment it happens, so a start with no matching end is
itself the evidence of a kill.

The files sit under `private/insights_profiler`, a sibling of `private/files`
that nothing serves over HTTP. The SQL a query ran is stored once per digest, so
a statement that failed can still be profiled later.
"""

import json
import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from hashlib import sha1

import frappe

SWITCH_KEY = "insights_profiler_recording_until"
# A worker asks Redis whether recording is on at most this often. The switch
# is read on every Insights request, and recording a minute late costs nothing.
SWITCH_CHECK_INTERVAL = 5
# A day's file stops growing past this, so a forgotten switch cannot fill the
# disk the warehouse spills to.
MAX_DAY_FILE_BYTES = 200 * 1024 * 1024
KEEP_DAYS = 7
MAX_RECORDING_MINUTES = 24 * 60

# site -> (checked at, recording until); a worker process can serve many sites
_switch_cache: dict[str, tuple[float, float]] = {}


def folder(*parts: str) -> str:
    """The profiler's folder for this site, created on first use."""
    path = frappe.get_site_path("private", "insights_profiler", *parts)
    os.makedirs(path, exist_ok=True)
    return os.path.realpath(path)


def recording() -> bool:
    """Whether events should be written right now, cheap enough for every request."""
    site = getattr(frappe.local, "site", None)
    if not site:
        return False
    checked_at, until = _switch_cache.get(site, (0.0, 0.0))
    if time.monotonic() - checked_at > SWITCH_CHECK_INTERVAL:
        until = float(frappe.cache.get_value(SWITCH_KEY) or 0)
        _switch_cache[site] = (time.monotonic(), until)
    return time.time() < until


def start_recording(minutes: int) -> float:
    """Record for the next `minutes`, and answer when it stops."""
    minutes = max(1, min(int(minutes), MAX_RECORDING_MINUTES))
    until = time.time() + minutes * 60
    frappe.cache.set_value(SWITCH_KEY, until, expires_in_sec=minutes * 60)
    _switch_cache.pop(frappe.local.site, None)
    prune()
    return until


def stop_recording() -> None:
    frappe.cache.delete_value(SWITCH_KEY)
    _switch_cache.pop(frappe.local.site, None)


def recording_until() -> float | None:
    until = float(frappe.cache.get_value(SWITCH_KEY) or 0)
    return until if until > time.time() else None


def write(event: dict) -> None:
    """Append one event as one line. Never raises into the caller."""
    try:
        path = _day_file(event["ts"])
        if os.path.exists(path) and os.path.getsize(path) > MAX_DAY_FILE_BYTES:
            return
        line = json.dumps(event, default=str, separators=(",", ":")) + "\n"
        with open(path, "a", encoding="utf-8") as f:  # nosemgrep - a dated file in this site's folder
            f.write(line)
    except Exception:
        frappe.logger("insights_profiler").warning("Could not write a profiler event", exc_info=True)


def save_sql(sql: str) -> str:
    """Store a statement once under its digest, and answer the digest."""
    digest = sql_digest(sql)
    path = os.path.join(folder("sql"), f"{digest}.sql")
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:  # nosemgrep - named by a hex digest
                f.write(sql)
        except OSError:
            frappe.logger("insights_profiler").warning("Could not save a statement", exc_info=True)
    return digest


def sql_digest(sql: str) -> str:
    return sha1(sql.encode("utf-8")).hexdigest()[:16]  # nosemgrep - a file name, not a secret


def read_sql(digest: str) -> str | None:
    if not digest.isalnum():
        return None
    path = os.path.join(folder("sql"), f"{digest}.sql")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:  # nosemgrep - the digest was checked alphanumeric above
        return f.read()


def read(since: float, until: float) -> Iterator[dict]:
    """Every event written between two epoch times, oldest file first."""
    day = _utc_day(since)
    while day <= _utc_day(until):
        yield from _read_day(day, since, until)
        day += timedelta(days=1)


def _read_day(day: datetime, since: float, until: float) -> Iterator[dict]:
    path = os.path.join(folder(), f"events-{day:%Y%m%d}.jsonl")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:  # nosemgrep - a dated file in this site's folder
        for line in f:
            try:
                event = json.loads(line)
            except ValueError:
                continue  # a line cut short by a kill mid-write
            if since <= event.get("ts", 0) <= until:
                yield event


def files() -> list[dict]:
    """The day files on disk, for the operator to see what is kept."""
    root = folder()
    return [
        {"file": name, "bytes": os.path.getsize(os.path.join(root, name))}
        for name in sorted(os.listdir(root))
        if name.startswith("events-")
    ]


def prune(keep_days: int = KEEP_DAYS) -> None:
    """Drop day files older than `keep_days`."""
    cutoff = f"events-{_utc_day(time.time()) - timedelta(days=keep_days):%Y%m%d}.jsonl"
    root = folder()
    for name in os.listdir(root):
        if name.startswith("events-") and name < cutoff:
            os.remove(os.path.join(root, name))


def _day_file(ts: float) -> str:
    return os.path.join(folder(), f"events-{_utc_day(ts):%Y%m%d}.jsonl")


def _utc_day(ts: float) -> datetime:
    moment = datetime.fromtimestamp(ts, UTC)
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)
