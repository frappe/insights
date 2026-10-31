# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import shutil
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from functools import cache
from urllib.parse import urlparse

import frappe
import ibis
from duckdb import ConnectionException, InterruptException, IOException
from frappe.utils import get_files_path
from ibis.backends.duckdb import Backend as DuckDBBackend
from ibis.backends.sql.compilers.duckdb import DuckDBCompiler

from insights.exceptions import QueryTimeout
from insights.resources import cpu_budget, memory_budget

from .compilers import StarExceptDropColumns

# DuckDB hands a file to one writer or to many readers, never both, and a read
# connection holds its shared lock until its request ends. A writer that arrives
# mid-request must therefore wait the readers out instead of failing on the
# first attempt.
#
# A reader in another process holds the file's lock. A reader in another thread of
# this process, as in a runner that serves requests and jobs in one process, holds
# DuckDB's shared instance open read-only instead, and a write open fails on its
# configuration. The writer waits out both.
#
# How long it may wait is the caller's business, not the file's. A writer serving
# a click must not hold a web worker while readers come and go, so the default
# stays short. A writer in a background job can afford to sit it out, and asks.
WRITE_LOCK_TIMEOUT = 30
IMPORT_WRITE_LOCK_TIMEOUT = 5 * 60
WRITE_LOCK_RETRY_INTERVAL = 1
READER_HELD_ERRORS = ("Could not set lock", "different configuration than existing connections")

# DuckDB defaults to 80% of host RAM and one thread per core, per process. With
# several web workers that is more than the host has: a warehouse compaction
# got OOM-killed, and one dashboard filled every core. So the data store gets
# half of what the server may use, split among the queries the slot pool lets
# run at once (`data_warehouse.data_store_slots`). Under its memory cap a query
# spills to `<db file>.tmp`. Sites can set the memory limit with this site
# config key.
MEMORY_LIMIT_CONFIG_KEY = "insights_duckdb_memory_limit"
DATA_STORE_SHARE = 0.5
# what the OS, MariaDB and the web workers' own Python keep, before the share
MEMORY_HEADROOM = 2 * 1024**3
MIN_MEMORY_LIMIT = 512 * 1024**2
# a query may spill this share of the disk that is free, split among the slots
TEMP_DISK_SHARE = 0.25


class InsightsDuckDBCompiler(StarExceptDropColumns, DuckDBCompiler):
    pass


def connect_duckdb(*args, **kwargs) -> DuckDBBackend:
    kwargs.setdefault("memory_limit", get_memory_limit())
    db = ibis.duckdb.connect(*args, **kwargs)
    db.compiler = InsightsDuckDBCompiler()
    # set, not passed to connect: connecting with settings that differ from those
    # of a connection already open on the same file fails, and an import commit
    # changes its threads
    db.raw_sql(f"SET threads = {get_threads()}")
    return db


class QueryTimeLimitExceeded(QueryTimeout):
    def __init__(self, seconds: int):
        super().__init__(
            f"Query execution time exceeded the limit of {seconds} seconds. Please try again with a smaller timespan or a more specific filter."
        )
        self.seconds = seconds


# how often a running query looks for a cancel: one Redis call per this many
# seconds while it runs, none for a query that ends sooner
CANCEL_POLL_INTERVAL = 0.5


@contextmanager
def time_limit(db: DuckDBBackend, seconds: float, cancelled=None):
    """Interrupt the query `db` runs once it has run `seconds`, or once
    `cancelled()` says its reader asked it to stop.

    DuckDB has no statement timeout, and a query that outlives the web tier's
    timeout gets its worker killed. An interrupted query raises, and the
    connection serves the next one.
    """
    lock = threading.Lock()
    state = {"running": True, "interrupted": None}
    finished = threading.Event()

    def interrupt(reason: str):
        with lock:
            if state["running"]:
                state["interrupted"] = reason
                db.con.interrupt()

    def watch():
        deadline = time.monotonic() + seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return interrupt("time_limit")
            if finished.wait(min(left, CANCEL_POLL_INTERVAL) if cancelled else left):
                return
            if cancelled and cancelled():
                return interrupt("cancelled")

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        yield
    except InterruptException as e:
        if state["interrupted"] == "time_limit":
            raise QueryTimeLimitExceeded(seconds) from e
        if state["interrupted"] == "cancelled":
            from insights.cancellation import raise_cancelled

            raise_cancelled(e)
        raise
    finally:
        with lock:
            state["running"] = False
        finished.set()


def get_duckdb_path(data_source) -> str:
    """Return the filesystem path to the .duckdb file for a local DuckDB data source."""
    db_name = data_source.database_name
    return os.path.join(get_files_path(is_private=1), f"{db_name}.duckdb")


def open_local_duckdb(
    path,
    read_only=True,
    allowed_dir=None,
    lock_timeout=WRITE_LOCK_TIMEOUT,
) -> DuckDBBackend:
    """Open a DuckDB connection at the given filesystem path.

    This is the single place that knows how to configure a local DuckDB
    connection. It opens through `connect_duckdb`, as every DuckDB connection
    Insights makes must.

    Args:
        path: Absolute path to the .duckdb file.
        read_only: Whether to open in read-only mode.
        allowed_dir: Directory to allow external file access from (write mode only).
        lock_timeout: Seconds a write open waits for readers to release the file.
    """
    if not os.path.exists(path):
        db = connect_duckdb(path)
        db.disconnect()

    db = connect_duckdb(path, read_only=True) if read_only else _connect_for_write(path, lock_timeout)

    private_folder = os.path.realpath(get_files_path(is_private=1))
    private_folder = _escape_sql_path(private_folder)
    db.raw_sql(f"SET home_directory='{private_folder}'")
    # a division by zero returns inf by default; live connections return NULL
    db.raw_sql("SET ieee_floating_point_ops = false")
    if read_only:
        # DuckDB's default lets one query fill 90% of the disk the site's files
        # are on. An import keeps it: its commit spills what it must
        db.raw_sql(f"SET max_temp_directory_size = '{get_temp_directory_limit(path)}B'")

    if not read_only and allowed_dir:
        resolved_dir = os.path.realpath(allowed_dir)
        resolved_dir_escaped = _escape_sql_path(resolved_dir)
        db.raw_sql(f"SET allowed_directories = ['{resolved_dir_escaped}']")
    else:
        db.raw_sql("SET enable_external_access = false")

    return db


def get_memory_limit() -> str:
    return frappe.conf.get(MEMORY_LIMIT_CONFIG_KEY) or f"{get_default_memory_limit()}B"


def get_default_memory_limit() -> int:
    """A process's share of the data store's memory. DuckDB applies its limit to
    the process, and each query that runs holds a slot, so with every slot taken
    in a different process, together they stay within the share."""
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import data_store_slots

    share = (memory_budget() - MEMORY_HEADROOM) * DATA_STORE_SHARE
    return max(int(share / data_store_slots()), MIN_MEMORY_LIMIT)


def get_threads() -> int:
    """Threads for a process's DuckDB: a quarter of the cores, 1 to 4. A slot
    usually holds a process's only query, so these are a query's threads. More
    finish one query sooner but let fewer run at once; the CPU a query costs
    does not change with its threads."""
    return max(1, min(int(cpu_budget()) // 4, 4))


def get_temp_directory_limit(path: str) -> int:
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import data_store_slots

    return int(_free_disk(os.path.dirname(path)) * TEMP_DISK_SHARE / data_store_slots())


@cache
def _free_disk(folder: str) -> int:
    return shutil.disk_usage(folder).free


def refused_by_writer(error: BaseException) -> BaseException | None:
    """The DuckDB error under `error` that refused a read because a writer holds
    the file, if that is why it failed. A read that is refused shows it with the
    same messages as a write that waits."""
    while error is not None:
        if isinstance(error, IOException | ConnectionException) and any(
            message in str(error) for message in READER_HELD_ERRORS
        ):
            return error
        error = error.__cause__ or error.__context__
    return None


def _connect_for_write(path: str, lock_timeout: float) -> DuckDBBackend:
    """Open path for writing, waiting out the readers that still hold it."""
    deadline = time.monotonic() + lock_timeout
    waited = False

    while True:
        try:
            return connect_duckdb(path, read_only=False)
        except (IOException, ConnectionException) as e:
            if not any(error in str(e) for error in READER_HELD_ERRORS) or time.monotonic() >= deadline:
                raise
            if not waited:
                waited = True
                frappe.logger().warning(f"Waiting for readers to release {os.path.basename(path)}")
            time.sleep(WRITE_LOCK_RETRY_INTERVAL)


@contextmanager
def local_duckdb_write_lock(
    path: str,
    cache_key: str,
    timeout: int = WRITE_LOCK_TIMEOUT,
) -> Generator[float, None, None]:
    """Serialize write access to a local DuckDB file.

    Holds a file-level lock and evicts the cached read-only connection for
    cache_key, so the caller is free to open the file for writing — or to
    replace the file altogether, as the warehouse compaction does.

    Yields whatever is left of timeout once the lock is in hand. Waiting off
    other writers and waiting off readers come out of the one budget, and the
    caller does not have to work that out for itself.

    Args:
        path: Absolute path to the .duckdb file.
        cache_key: The key under which the read connection is cached in
            insights.db_connections (typically the data source name).
        timeout: Seconds to spend reaching a writable file, lock and readers
            together.
    """
    from frappe.utils.synchronization import filelock

    import insights

    deadline = time.monotonic() + timeout
    lock_name = f"insights_duckdb_write_{frappe.scrub(os.path.basename(path))}"
    with filelock(lock_name, timeout=timeout):
        with suppress(Exception):  # nosemgrep - the write open waits for, or fails on, a connection left open
            cached = insights.db_connections.pop(cache_key, None)
            if cached:
                cached.disconnect()

        yield max(deadline - time.monotonic(), 0)


@contextmanager
def local_duckdb_write_connection(
    path: str,
    cache_key: str,
    allowed_dir: str,
    timeout: int = WRITE_LOCK_TIMEOUT,
) -> Generator[DuckDBBackend, None, None]:
    """Context manager that safely yields a write connection to a local DuckDB file.

    DuckDB rejects a second connection to the same file when the existing
    connection has a different read_only setting. This function handles that by:
    1. Acquiring a file-level lock to serialize write access.
    2. Evicting and disconnecting any cached read-only connection for cache_key
       from insights.db_connections.
    3. Opening a fresh write connection and yielding it.
    4. Disconnecting on exit so the next read access re-opens cleanly.

    Args:
        path: Absolute path to the .duckdb file.
        cache_key: The key under which the read connection is cached in
            insights.db_connections (typically the data source name).
        allowed_dir: Directory to allow external file access from.
        timeout: Total seconds to spend obtaining the write connection, lock
            and readers together.
    """
    with local_duckdb_write_lock(path, cache_key, timeout=timeout) as lock_timeout:
        db = open_local_duckdb(
            path,
            read_only=False,
            allowed_dir=allowed_dir,
            lock_timeout=lock_timeout,
        )
        try:
            yield db
        finally:
            db.disconnect()


def get_duckdb_connection(data_source) -> DuckDBBackend:
    name = data_source.name or frappe.scrub(data_source.title)
    db_name = data_source.database_name

    if db_name.startswith("http"):
        return get_http_duckdb_connection(data_source, name, db_name)

    path = get_duckdb_path(data_source)
    return open_local_duckdb(path)


# Backward-compatible alias — prefer open_local_duckdb for new code
get_local_duckdb_connection = open_local_duckdb


def get_http_duckdb_connection(data_source, name, db_name):
    """Connect to a remote DuckDB via HTTP or DuckLake."""
    db = connect_duckdb()
    sql = get_http_secret(data_source, name, db_name)
    sql and db.raw_sql(sql)
    attach_url = f"ducklake:{db_name}" if data_source.is_ducklake else db_name
    db.attach(attach_url, name, read_only=True)
    db.raw_sql(f"USE '{name}'")
    db.raw_sql("SET enable_external_access=false")
    db.raw_sql("SET ieee_floating_point_ops = false")
    return db


def get_http_secret(data_source, name, db_name):
    headers = data_source.get("http_headers") or {}
    if not headers:
        return

    try:
        parsed = urlparse(db_name)
        scope = f"{parsed.scheme}://{parsed.netloc}"
        secret_name = f"http_auth_{frappe.scrub(name)}"
        scope_escaped = scope.replace("'", "''")

        headers = frappe.parse_json(headers) if isinstance(headers, str) else headers
        headers_str = ", ".join(f"'{k}': '{v}'" for k, v in headers.items())

        return f"""
            CREATE OR REPLACE SECRET {secret_name} (
                TYPE HTTP,
                SCOPE '{scope_escaped}',
                EXTRA_HTTP_HEADERS MAP {{ {headers_str} }}
            );
        """
    except Exception as e:
        frappe.log_error(title="Error creating HTTP Secret for DuckDB", message=str(e))
        return


def _escape_sql_path(path: str) -> str:
    return path.replace("'", "''")
