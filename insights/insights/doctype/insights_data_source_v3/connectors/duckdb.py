# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
from contextlib import suppress
from urllib.parse import urlparse

import frappe
import ibis
from frappe.utils import get_files_path


def get_duckdb_connection(data_source, read_only=True, allowed_dir=None, allow_private_files=False):
    name = data_source.name or frappe.scrub(data_source.title)
    db_name = data_source.database_name

    if db_name.startswith("http"):
        return get_http_duckdb_connection(data_source, name, db_name)

    path = os.path.join(get_files_path(is_private=1), f"{db_name}.duckdb")
    return get_local_duckdb_connection(
        path, read_only=read_only, allowed_dir=allowed_dir, allow_private_files=allow_private_files
    )


def get_local_duckdb_connection(path, read_only=True, allowed_dir=None, allow_private_files=False):
    if not os.path.exists(path):
        db = ibis.duckdb.connect(path)
        db.disconnect()

    db = ibis.duckdb.connect(path, read_only=read_only)

    private_folder = os.path.realpath(get_files_path(is_private=1))
    private_folder = _escape_sql_path(private_folder)
    db.raw_sql(f"SET home_directory='{private_folder}'")

    if not read_only and (allowed_dir or allow_private_files):
        allowed_dir = _escape_sql_path(allowed_dir) if allowed_dir else private_folder

        with suppress(Exception):
            db.raw_sql("SET enable_external_access = true")

        db.raw_sql(f"SET allowed_directories = ['{allowed_dir}']")
    else:
        db.raw_sql("SET enable_external_access = false")

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


def _escape_sql_path(path: str) -> str:
    return path.replace("'", "''")
