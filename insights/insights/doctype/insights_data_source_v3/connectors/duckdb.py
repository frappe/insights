# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
from contextlib import contextmanager
from urllib.parse import urlparse

import frappe
import ibis
from frappe.utils import get_files_path


@contextmanager
def external_access(allowed_dir: str):
    """Create a short-lived DuckDB connection with file access restricted to a single directory"""
    escaped_str = allowed_dir.replace("'", "''")
    conn = ibis.duckdb.connect()
    conn.raw_sql(f"SET home_directory='{escaped_str}'")
    conn.raw_sql(f"SET allowed_directories = ['{escaped_str}']")
    try:
        yield conn
    finally:
        conn.disconnect()


def get_duckdb_connection(data_source, read_only=True):
    name = data_source.name or frappe.scrub(data_source.title)
    db_name = data_source.database_name

    if db_name.startswith("http"):
        return get_http_duckdb_connection(data_source, name, db_name)

    return get_local_duckdb_connection(db_name, read_only=read_only)


def get_local_duckdb_connection(db_name, read_only=True):
    private_folder = os.path.realpath(get_files_path(is_private=1))
    path = os.path.join(private_folder, f"{db_name}.duckdb")

    if not os.path.exists(path):
        db = ibis.duckdb.connect(path)
        db.disconnect()

    db = ibis.duckdb.connect(path, read_only=read_only, enable_external_access=False)
    db.raw_sql(f"SET home_directory='{private_folder}'")

    return db


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
