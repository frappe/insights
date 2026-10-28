# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Run a profile in a background worker, and keep its report.

A profile replays statements that can each take minutes, then reruns them under
experiments, so it would outlive any web request's timeout. It runs on the
`long` queue, writes how far it got as it goes, and saves the report to disk.

Run it off-peak: it does on purpose what a heavy dashboard does by accident.
"""

import json
import os
import time
import traceback
from typing import Any
from uuid import uuid4

import frappe

import insights
from insights.profiler import environment, events, findings, statement, targets

QUEUE = "long"
JOB_TIMEOUT = 3 * 60 * 60
BROWSER_IN_FLIGHT = 6  # frontend/src2/query/execution_queue.ts, MAX_IN_FLIGHT
DEFAULTS = {
    "max_seconds": 300,
    "experiments": ["threads", "insertion_order", "concurrency"],
    "experiment_statements": 1,
    "copies": [1, 2, 4, BROWSER_IN_FLIGHT],
    "load": True,
    "layouts": True,
}


def start(target: dict, options: dict | None = None) -> str:
    """Queue a profile and answer its id."""
    profile_id = uuid4().hex[:12]
    options = {**DEFAULTS, **(options or {})}
    _status(profile_id, state="queued", target=target, options=options, by=frappe.session.user)
    frappe.enqueue(
        "insights.profiler.job.run",
        queue=QUEUE,
        timeout=JOB_TIMEOUT,
        job_id=_job_id(profile_id),
        profile_id=profile_id,
        target=target,
        options=options,
    )
    return profile_id


def run(profile_id: str, target: dict, options: dict) -> None:
    """The job: build the report, or record why it could not."""
    try:
        report = build(profile_id, target, options)
        _write(profile_id, "report", report)
        _status(profile_id, state="finished", findings=len(report["findings"]))
    except Exception:
        _status(profile_id, state="failed", error=traceback.format_exc()[-4000:])
        raise


def build(profile_id: str, target: dict, options: dict) -> dict[str, Any]:
    started = time.time()
    _status(profile_id, state="running", step="Reading the warehouse, bench and host")
    env = environment.snapshot()
    _status(profile_id, step="Building the statements")
    resolved = targets.resolve(target)
    report = {"id": profile_id, "target": target, "options": options, "environment": env, **resolved}
    _profile_statements(profile_id, report["statements"], options)
    if target.get("dashboard") and options["load"]:
        _status(profile_id, step="Loading the dashboard six statements at a time")
        report["load"] = dashboard_load(report, options)
    report["findings"] = findings.derive(report)
    report["seconds"] = round(time.time() - started, 1)
    for s in report["statements"]:
        s.pop("sql", None)  # kept once under its digest; `get_sql` reads it back
    return report


def _profile_statements(profile_id: str, statements: list[dict], options: dict) -> None:
    con = insights.warehouse.db.con
    runnable = [s for s in statements if s["data_store"]]
    for n, s in enumerate(runnable, 1):
        _status(profile_id, step=f"Profiling statement {n} of {len(runnable)} alone")
        s["alone"] = statement.profile(con, s["sql"], options["max_seconds"])
    for s in statements:
        s.setdefault("alone", {"skipped": "reads a live source, not the data store"})
    costliest = sorted(runnable, key=lambda s: s["alone"]["wall_s"], reverse=True)
    for s in costliest[: max(0, int(options["experiment_statements"]))]:
        _status(profile_id, step=f"Running experiments on {s['digest']}")
        s["experiments"] = experiments(con, s["sql"], options)
        if options["layouts"]:
            s["layouts"] = layouts(con, s["alone"])


def experiments(con, sql: str, options: dict) -> dict[str, Any]:
    """The statement under other settings and at other concurrency."""
    limit, chosen = options["max_seconds"], options["experiments"]
    cpus = int(environment.host().get("cpu_limit") or os.cpu_count() or 1)
    found: dict[str, Any] = {}
    # one untimed run first, so the first setting tried is not also the only cold one
    statement.light_run(con, sql, limit)
    if "threads" in chosen:
        found["threads"] = statement.threads_sweep(con, sql, sorted({1, 2, 4, cpus}), limit)
    if "insertion_order" in chosen:
        found["insertion_order"] = statement.insertion_order(con, sql, limit)
    if "concurrency" in chosen:
        found["concurrency"] = statement.concurrency_sweep(con, sql, options["copies"], limit)
    return found


def layouts(con, alone: dict) -> list[dict]:
    """How the date columns the costliest scans filter on are laid out on disk."""
    seen, found = set(), []
    for scan in (alone.get("plan") or {}).get("scans", []):
        for bound in scan["date_bounds"]:
            key = (scan["table"], bound["column"])
            qualified = environment.qualified_table(scan["table"])
            if key in seen or not qualified or bound["operator"] not in (">=", ">"):
                continue
            seen.add(key)
            layout = statement.date_layout(con, qualified, bound["column"], bound["value"])
            found.append(
                {"table": scan["table"], "column": bound["column"], "bound": bound["value"], **layout}
            )
    return found


LOAD_NOTE = (
    "One process ran every statement here, on one DuckDB instance under one memory limit. "
    "A real load is spread over the web workers, each with its own instance and limit, so this "
    "understates memory and overstates contention for one instance's threads. "
    "The replay over HTTP measures the real thing."
)


def dashboard_load(report: dict, options: dict) -> dict[str, Any]:
    """Every statement the charts run, in chart order, six at a time like the browser."""
    sql_by_digest = {s["digest"]: s["sql"] for s in report["statements"] if s["data_store"]}
    order = [p["digest"] for c in report["charts"] for p in c["statements"] if p["digest"] in sql_by_digest]
    con = insights.warehouse.db.con
    result = statement.together(
        con, [sql_by_digest[d] for d in order], BROWSER_IN_FLIGHT, options["max_seconds"]
    )
    for run, digest in zip(result["runs"], order, strict=True):
        run["digest"] = digest
    return {**result, "in_flight": BROWSER_IN_FLIGHT, "note": LOAD_NOTE}


# --- storage ------------------------------------------------------------------


def status(profile_id: str) -> dict | None:
    """How far a profile got. One whose worker died still says `running` on
    disk, so that is checked against the queue."""
    found = _read(profile_id, "status")
    if found and found.get("state") in ("queued", "running") and not _job_alive(profile_id):
        found = {
            **found,
            "state": "stopped",
            "error": "The job is no longer queued or running: its worker stopped",
        }
    return found


def _job_alive(profile_id: str) -> bool:
    from frappe.utils.background_jobs import is_job_enqueued

    return is_job_enqueued(_job_id(profile_id))


def _job_id(profile_id: str) -> str:
    return f"insights_profile_{profile_id}"


def report(profile_id: str) -> dict | None:
    return _read(profile_id, "report")


def recent(limit: int = 20) -> list[dict]:
    root = events.folder("profiles")
    names = sorted(
        (n for n in os.listdir(root) if n.endswith(".status.json")),
        key=lambda n: os.path.getmtime(os.path.join(root, n)),
        reverse=True,
    )
    return [status(n.split(".")[0]) for n in names[:limit]]


def _status(profile_id: str, **fields) -> None:
    current = _read(profile_id, "status") or {"id": profile_id, "queued_at": time.time()}
    _write(profile_id, "status", {**current, **fields, "updated_at": time.time()})


def _write(profile_id: str, kind: str, data: dict) -> None:
    path = os.path.join(events.folder("profiles"), f"{profile_id}.{kind}.json")
    with open(f"{path}.part", "w", encoding="utf-8") as f:  # nosemgrep - our own profile id
        json.dump(data, f, default=str)
    os.replace(f"{path}.part", path)


def _read(profile_id: str, kind: str) -> dict | None:
    if not profile_id.isalnum():
        return None
    path = os.path.join(events.folder("profiles"), f"{profile_id}.{kind}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:  # nosemgrep - the profile id was checked alphanumeric above
        return json.load(f)
