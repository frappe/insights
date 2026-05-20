# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
from collections.abc import Generator
from contextlib import contextmanager, suppress
from urllib.parse import urlparse

import frappe
import ibis
from frappe.utils import get_files_path
from ibis.backends.duckdb import Backend as DuckDBBackend


def get_duckdb_path(data_source) -> str:
    """Return the filesystem path to the .duckdb file for a local DuckDB data source."""
    db_name = data_source.database_name
    return os.path.join(get_files_path(is_private=1), f"{db_name}.duckdb")


def open_local_duckdb(
    path,
    read_only=True,
    allowed_dir=None,
) -> DuckDBBackend:
    """Open a DuckDB connection at the given filesystem path.

    This is the single place that knows how to configure a local DuckDB
    connection. Do not call ibis.duckdb.connect() directly anywhere else.

    Args:
        path: Absolute path to the .duckdb file.
        read_only: Whether to open in read-only mode.
        allowed_dir: Directory to allow external file access from (write mode only).
    """
    if not os.path.exists(path):
        db = ibis.duckdb.connect(path)
        db.disconnect()

    db = ibis.duckdb.connect(path, read_only=read_only)

    private_folder = os.path.realpath(get_files_path(is_private=1))
    private_folder = _escape_sql_path(private_folder)
    db.raw_sql(f"SET home_directory='{private_folder}'")

    if not read_only and allowed_dir:
        resolved_dir = os.path.realpath(allowed_dir)
        resolved_dir_escaped = _escape_sql_path(resolved_dir)

        with suppress(Exception):
            db.raw_sql("SET enable_external_access = true")

        db.raw_sql(f"SET allowed_directories = ['{resolved_dir_escaped}']")
    else:
        db.raw_sql("SET enable_external_access = false")

    return db


@contextmanager
def local_duckdb_write_connection(
    path: str,
    cache_key: str,
    allowed_dir: str,
    timeout: int = 30,
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
        timeout: Seconds to wait for the file lock before giving up.
    """
    from frappe.utils.synchronization import filelock

    import insights

    lock_name = f"insights_duckdb_write_{frappe.scrub(os.path.basename(path))}"
    with filelock(lock_name, timeout=timeout):
        with suppress(Exception):
            cached = insights.db_connections.pop(cache_key, None)
            if cached:
                cached.disconnect()

        db = open_local_duckdb(
            path,
            read_only=False,
            allowed_dir=allowed_dir,
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
    db = ibis.duckdb.connect()
    sql = get_http_secret(data_source, name, db_name)
    sql and db.raw_sql(sql)
    attach_url = f"ducklake:{db_name}" if data_source.is_ducklake else db_name
    db.attach(attach_url, name, read_only=True)
    db.raw_sql(f"USE '{name}'")
    db.raw_sql("SET enable_external_access=false")
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
