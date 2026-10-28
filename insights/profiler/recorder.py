# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Write a start and an end for everything that can load the data store.

Four kinds of event, each a pair sharing an `id`:

- `request` — an Insights call over HTTP: who, which endpoint, which chart and
  dashboard, the status it answered and how long it took
- `query` — one statement through `execute_ibis_query`: the cache outcome, the
  compile and execution time, the rows, the CPU and memory the process used
- `connect` — one open of a DuckDB file: how long it waited, and whether a
  writer's lock refused it
- `job` — one Insights background job

A start with no end means the work never finished: the worker was killed by
the request timeout or the kernel, or a job failed. `report` tells those apart.

Every function here returns at once while recording is off, and none of them
lets an error of its own reach the work it watches.
"""

import os
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from functools import cache
from uuid import uuid4

import frappe
import psutil

from insights.profiler import events

# names a request may carry that tell which content it loaded
CONTEXT_FIELDS = ("chart", "chart_name", "dashboard", "query", "workbook")
MAX_FIELD_LENGTH = 140

_in_flight = 0
_in_flight_lock = threading.Lock()


def _process() -> psutil.Process:
    # keyed by pid: gunicorn forks its workers, and a handle cached before the
    # fork would describe the parent
    return _process_for(os.getpid())


@cache
def _process_for(pid: int) -> psutil.Process:
    return psutil.Process(pid)


def process_stamp() -> dict:
    """Who is doing the work: the process, its start time and the thread.

    The start time lets a reader tell a dead worker from a new one that reused
    its pid.
    """
    proc = _process()
    return {"pid": proc.pid, "pid_started": proc.create_time(), "thread": threading.get_ident()}


def resource_reading() -> dict:
    """This process's CPU seconds so far and its resident memory."""
    proc = _process()
    cpu = proc.cpu_times()
    return {"cpu": cpu.user + cpu.system, "rss": proc.memory_info().rss}


def _new_event(kind: str, **fields) -> dict:
    return {
        "id": uuid4().hex[:16],
        "kind": kind,
        "ts": time.time(),
        "site": frappe.local.site,
        "user": getattr(getattr(frappe.local, "session", None), "user", None),
        **process_stamp(),
        **fields,
    }


def _end_event(start: dict, **fields) -> dict:
    """The matching end: same id, and how long since the start."""
    now = time.time()
    return {
        "id": start["id"],
        "kind": f"{start['kind']}.end",
        "ts": now,
        "duration": round(now - start["ts"], 4),
        **fields,
    }


def _clip(value) -> str | None:
    if value is None:
        return None
    return str(value)[:MAX_FIELD_LENGTH]


# --- requests -----------------------------------------------------------------


def is_insights_request() -> bool:
    """Whether this request reads or runs Insights content."""
    request = getattr(frappe.local, "request", None)
    if request is None:
        return False
    if "insights" in request.path.lower():
        return True
    form = frappe.local.form_dict or {}
    return str(form.get("dt") or form.get("doctype") or "").startswith("Insights")


def request_context() -> dict:
    """The names a request carries that say which content it loaded."""
    form = frappe.local.form_dict or {}
    context = {field: _clip(form.get(field)) for field in CONTEXT_FIELDS if form.get(field)}
    request = frappe.local.request
    return {"path": request.path, "method": request.method, **context}


def before_request():
    """Hook: open a `request` event for an Insights call while recording."""
    try:
        if not is_insights_request() or not events.recording():
            return
        event = _new_event("request", **request_context(), start=resource_reading())
        frappe.local.insights_profiler_request = event
        events.write(event)
    except Exception:
        frappe.logger("insights_profiler").warning("Could not record a request start", exc_info=True)


def after_request(response=None, request=None):
    """Hook: close the request's event with its status and what it cost."""
    start = getattr(frappe.local, "insights_profiler_request", None)
    if not start:
        return
    try:
        frappe.local.insights_profiler_request = None
        status = getattr(response, "status_code", None)
        events.write(
            _end_event(start, status=status, error=_response_error(response, status), **_cost(start))
        )
    except Exception:
        frappe.logger("insights_profiler").warning("Could not record a request end", exc_info=True)


def _response_error(response, status: int | None) -> str | None:
    """The exception type a failed Frappe response names, if it names one."""
    if not status or status < 400 or response is None:
        return None
    try:
        body = response.get_data(as_text=True)
        if len(body) > 65536:
            return None
        return _clip(frappe.parse_json(body).get("exc_type"))
    except Exception:
        return None  # nosemgrep - a body that is not Frappe's JSON names no exception type


def _cost(start: dict) -> dict:
    now = resource_reading()
    before = start.get("start") or now
    return {"cpu_s": round(now["cpu"] - before["cpu"], 3), "rss_start": before["rss"], "rss_end": now["rss"]}


# --- background jobs ----------------------------------------------------------


def before_job(method=None, **kwargs):
    """Hook: open a `job` event for an Insights background job while recording."""
    try:
        if not str(method or "").startswith("insights.") or not events.recording():
            return
        event = _new_event("job", method=_clip(method), start=resource_reading())
        frappe.local.insights_profiler_job = event
        events.write(event)
    except Exception:
        frappe.logger("insights_profiler").warning("Could not record a job start", exc_info=True)


def after_job(method=None, **kwargs):
    """Hook: close the job's event. A job that raised never reaches this."""
    start = getattr(frappe.local, "insights_profiler_job", None)
    if not start:
        return
    try:
        frappe.local.insights_profiler_job = None
        events.write(_end_event(start, **_cost(start)))
    except Exception:
        frappe.logger("insights_profiler").warning("Could not record a job end", exc_info=True)


# --- queries and connections --------------------------------------------------


@contextmanager
def record_query(
    sql: str, *, data_store: bool, reference: str | None, **known
) -> Generator[dict, None, None]:
    """Record one statement's run, or one answer from the result cache.

    `known` is what the caller already knows when the run starts, such as
    `cache` and `compile_s`. The dict it yields takes what is learned during the
    run, such as `rows`, and is always safe to write to, so the caller does not
    need to know whether recording is on.
    """
    outcome: dict = dict(known)
    if not events.recording():
        yield outcome
        return

    start = _query_start(sql, data_store, reference)
    error = None
    try:
        yield outcome
    except BaseException as e:
        error = e
        raise
    finally:
        _query_end(start, outcome, error)


def _query_start(sql: str, data_store: bool, reference: str | None) -> dict:
    global _in_flight
    with _in_flight_lock:
        _in_flight += 1
        in_flight = _in_flight
    event = _new_event(
        "query",
        sql=events.save_sql(sql),
        sql_bytes=len(sql),
        source="data_store" if data_store else "live",
        reference=_clip(reference),
        in_flight_process=in_flight,
        **_owner(),
        start=resource_reading(),
    )
    events.write(event)
    return event


def _query_end(start: dict, outcome: dict, error: BaseException | None) -> None:
    global _in_flight
    with _in_flight_lock:
        _in_flight -= 1
    fields = {**outcome, **_cost(start)}
    if error is not None:
        fields.update(
            error_type=type(error).__name__, error=_clip(str(error).splitlines()[0] if str(error) else "")
        )
    events.write(_end_event(start, ok=error is None, **fields))


def _owner() -> dict:
    """The request or job a query ran for, so a report can group it by dashboard."""
    request = getattr(frappe.local, "insights_profiler_request", None)
    if request:
        return {"request": request["id"], **{f: request[f] for f in CONTEXT_FIELDS if request.get(f)}}
    job = getattr(frappe.local, "insights_profiler_job", None)
    if job:
        return {"job": job["id"], "job_method": job["method"]}
    return {}


@contextmanager
def record_connection(path: str, *, read_only: bool) -> Generator[None, None, None]:
    """Record one open of a DuckDB file, and whether a lock refused it."""
    if not events.recording():
        yield
        return

    start = _new_event("connect", file=os.path.basename(path), read_only=read_only, **_owner())
    error = None
    try:
        yield
    except BaseException as e:
        error = e
        raise
    finally:
        fields = {"ok": not error, "duration": round(time.time() - start["ts"], 4)}
        if error is not None:
            message = str(error).splitlines()[0] if str(error) else ""
            fields.update(
                error_type=type(error).__name__, error=_clip(message), lock="lock" in message.lower()
            )
        # one line, written at the end: an open is short, and what matters is
        # how long it waited and whether it got in
        events.write({**start, **fields})
