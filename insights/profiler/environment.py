# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What the warehouse, the bench and the host look like at one moment.

Each section stands alone and reports its own failure in place, so a host
that hides `/proc` or a missing cgroup file costs one section, not the report.
"""

import os
import re
import time
from collections.abc import Callable
from typing import Any

import frappe
import psutil
from frappe.utils import add_to_date, now_datetime

import insights

DUCKDB_SETTINGS = (
    "threads",
    "external_threads",
    "memory_limit",
    "max_memory",
    "temp_directory",
    "max_temp_directory_size",
    "preserve_insertion_order",
    "enable_object_cache",
    "checkpoint_threshold",
    "default_order",
)
CPU_SAMPLE_SECONDS = 1.0
TOP_TABLES = 100


def snapshot() -> dict[str, Any]:
    """Every section, each answering on its own."""
    sections: dict[str, Callable[[], Any]] = {
        "duckdb": duckdb_state,
        "tables": table_sizes,
        "web": web_tier,
        "processes": bench_processes,
        "host": host,
        "background": background_jobs,
        "imports": recent_imports,
    }
    return {name: _guarded(read) for name, read in sections.items()}


def _guarded(read: Callable[[], Any]) -> Any:
    try:
        return read()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"[:300]}


# --- the warehouse ------------------------------------------------------------


def duckdb_state() -> dict:
    """Version, the settings that bound a query, and the files on disk."""
    con = insights.warehouse.db.con
    names = ", ".join(f"'{n}'" for n in DUCKDB_SETTINGS)
    settings = dict(
        con.execute(f"SELECT name, value FROM duckdb_settings() WHERE name IN ({names})").fetchall()
    )
    path = insights.warehouse.get_db_path()
    return {
        "version": con.execute("SELECT version()").fetchone()[0],
        "settings": settings,
        "files": {
            "database_bytes": _size(path),
            "wal_bytes": _size(f"{path}.wal"),
            "spill_bytes": _tree_size(f"{path}.tmp"),
        },
    }


def table_sizes() -> list[dict]:
    """The largest warehouse tables by DuckDB's own row count, not the import log's."""
    rows = insights.warehouse.db.con.execute(
        """
        SELECT schema_name, table_name, estimated_size, column_count
        FROM duckdb_tables()
        ORDER BY estimated_size DESC
        LIMIT ?
        """,
        [TOP_TABLES],
    ).fetchall()
    return [{"schema": s, "table": t, "rows": n, "columns": c} for s, t, n, c in rows]


def qualified_table(table: str) -> str | None:
    """`schema.table` for a bare table name a plan reports, if it names one table."""
    rows = (
        insights.warehouse.db.con.cursor()
        .execute("SELECT schema_name FROM duckdb_tables() WHERE table_name = ?", [table])
        .fetchall()
    )
    return f'"{rows[0][0]}"."{table}"' if len(rows) == 1 else None


def _size(path: str) -> int | None:
    return os.path.getsize(path) if os.path.exists(path) else None


def _tree_size(path: str) -> int:
    if not os.path.isdir(path):
        return 0
    return sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(path) for f in files)


# --- the bench ----------------------------------------------------------------


def web_tier() -> dict:
    """Gunicorn's workers, threads and timeout, read off its own command line."""
    for proc in psutil.process_iter(["cmdline"]):
        cmdline = proc.info["cmdline"] or []
        if _is_gunicorn_master(proc, cmdline):
            return {
                "workers": _flag(cmdline, "-w", "--workers") or 1,
                "threads": _flag(cmdline, "--threads") or 1,
                "timeout": _flag(cmdline, "-t", "--timeout") or 30,
                "worker_class": _flag(cmdline, "-k", "--worker-class", cast=str) or "sync",
                "cmdline": " ".join(cmdline)[:500],
            }
    return {"error": "no gunicorn master is visible from this process"}


def _is_gunicorn_master(proc: psutil.Process, cmdline: list[str]) -> bool:
    if not any("gunicorn" in part for part in cmdline):
        return False
    try:
        parent = proc.parent()
        return parent is None or not any("gunicorn" in p for p in (parent.cmdline() or []))
    except psutil.Error:
        return False  # nosemgrep - a parent that vanished is not a gunicorn master


def _flag(args: list[str], *names: str, cast=int):
    for i, arg in enumerate(args):
        for name in names:
            value = args[i + 1] if arg == name and i + 1 < len(args) else None
            value = arg.split("=", 1)[1] if arg.startswith(f"{name}=") else value
            if value is not None:
                try:
                    return cast(value)
                except ValueError:
                    return None  # nosemgrep - a flag that is not a number is one gunicorn would refuse
    return None


def bench_processes() -> list[dict]:
    """Every bench process with what it is, its memory, and its CPU over one second."""
    procs = [(p, _role(p)) for p in psutil.process_iter(["pid", "cmdline", "create_time"])]
    procs = [(p, role) for p, role in procs if role]
    for p, _ in procs:
        _quietly(p.cpu_percent, None)
    time.sleep(CPU_SAMPLE_SECONDS)
    found = [_describe(p, role) for p, role in procs]
    return sorted((f for f in found if f), key=lambda f: f["cpu_percent"], reverse=True)


def _role(proc: psutil.Process) -> str | None:
    text = " ".join(proc.info.get("cmdline") or [])
    if "gunicorn" in text:
        return "web"
    if "redis-server" in text:
        return "redis"
    if "socketio" in text:
        return "socketio"
    if "frappe" not in text and "bench" not in text:
        return None
    if " serve" in text:
        return "web"  # the development server, which `bench start` runs in place of gunicorn
    if " worker" in text:
        queue = re.search(r"--queue[= ]([\w,]+)", text)
        return f"worker:{queue.group(1)}" if queue else "worker"
    return "scheduler" if "schedule" in text else None


def _describe(proc: psutil.Process, role: str) -> dict | None:
    try:
        with proc.oneshot():
            return {
                "pid": proc.pid,
                "role": role,
                "cpu_percent": proc.cpu_percent(None),
                "rss": proc.memory_info().rss,
                "threads": proc.num_threads(),
                "started": proc.create_time(),
            }
    except psutil.Error:
        return None  # nosemgrep - a process that exited between listing and reading it is gone


def _quietly(fn, *args):
    try:
        return fn(*args)
    except psutil.Error:
        return None  # nosemgrep - a process that exited before its first CPU reading is gone


# --- the host -----------------------------------------------------------------


def host() -> dict:
    """CPU and memory as the host and as this container's limits see them."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(frappe.get_site_path())
    return {
        "cpu_count": os.cpu_count(),
        "cpu_limit": _cgroup_cpu_limit(),
        "load_average": [round(x, 2) for x in os.getloadavg()],
        "memory_total": memory.total,
        "memory_available": memory.available,
        "memory_limit": _read_int("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"),
        "memory_used_by_container": _read_int(
            "/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory/memory.usage_in_bytes"
        ),
        "disk_free": disk.free,
    }


def _cgroup_cpu_limit() -> float | None:
    """The CPUs this container may use, when a quota caps it."""
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:  # nosemgrep - a fixed file of the container's own cgroup
            quota, period = f.read().split()
        return None if quota == "max" else round(int(quota) / int(period), 2)
    except (OSError, ValueError):
        return None  # nosemgrep - no readable quota means no limit beyond the host's CPUs


def _read_int(*paths: str) -> int | None:
    for path in paths:
        try:
            with open(path) as f:  # nosemgrep - one of the fixed cgroup files named by the caller
                value = f.read().strip()
            return None if value == "max" else int(value)
        except (OSError, ValueError):
            continue
    return None


# --- work in the background ---------------------------------------------------


def background_jobs() -> dict:
    """What each worker is running now, and how many jobs wait in each queue."""
    from frappe.utils.background_jobs import get_queue_args, get_queues, get_workers

    workers = []
    for worker in get_workers():
        job = worker.get_current_job()
        workers.append(
            {
                "name": worker.name,
                "queues": worker.queue_names(),
                "state": worker.get_state(),
                "job": job and (get_queue_args(job).get("job_name") or job.func_name),
                "site": job and get_queue_args(job).get("site"),
                "job_started": job and job.started_at,
            }
        )
    return {"workers": workers, "queued": {q.name: q.count for q in get_queues()}}


def recent_imports(hours: int = 24) -> list[dict]:
    """Imports of the last `hours`: each one held the warehouse's write lock to commit."""
    return frappe.get_all(
        "Insights Table Import Log",
        filters={"creation": [">", add_to_date(now_datetime(), hours=-hours)]},
        fields=[
            "table_name",
            "data_source",
            "status",
            "started_at",
            "ended_at",
            "time_taken",
            "rows_imported",
        ],
        order_by="started_at desc",
        limit=200,
    )
