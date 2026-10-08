import json
import os
import tempfile
from collections import defaultdict
from contextlib import suppress
from pathlib import Path

import frappe
from frappe.utils import get_datetime_str, now_datetime
from frappe.utils.background_jobs import is_job_enqueued
from ibis.backends.duckdb import Backend as DuckDBBackend

import insights

STORAGE_FILE_NAME = "storage.json"
MEASURE_JOB_ID = "measure_data_store"


def measure_table(db: DuckDBBackend, schema: str, table: str) -> dict:
    """Bytes a table holds in the file, in total and per column.

    A block can hold small segments of several columns, so each block is split
    evenly between the columns that use it. String overflow blocks belong to
    one column and land on it whole. Column bytes then sum to the table's
    distinct blocks, which is what dropping the table would free. Segments
    with a negative `block_id` are constant and take no block.

    Reads persisted segments only: call after a `CHECKPOINT`.
    """
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
        escape_sql_string,
        quote_identifier,
    )

    qualified = f"{quote_identifier(schema)}.{quote_identifier(table)}"
    block_size = get_block_size(db)

    segments = db.raw_sql(
        "select column_name, block_id, additional_block_ids "
        f"from pragma_storage_info('{escape_sql_string(qualified)}')"
    ).fetchall()

    columns_per_block: dict[int, set[str]] = defaultdict(set)
    columns: dict[str, int] = {}
    for column, block_id, additional_block_ids in segments:
        columns.setdefault(column, 0)
        for block in [block_id, *(additional_block_ids or [])]:
            if block is not None and block >= 0:
                columns_per_block[block].add(column)

    for users in columns_per_block.values():
        share, remainder = divmod(block_size, len(users))
        for i, column in enumerate(sorted(users)):
            columns[column] += share + (1 if i < remainder else 0)

    rows = db.raw_sql(f"select count(*) from {qualified}").fetchone()[0]

    return {
        "bytes": len(columns_per_block) * block_size,
        "rows": int(rows),
        "columns": columns,
        "measured_on": get_datetime_str(now_datetime().replace(microsecond=0)),
    }


def record_table_storage(db: DuckDBBackend, schema: str, table: str) -> None:
    """Measure one table after a write and update its entry in `storage.json`.

    The caller holds the warehouse write lock, which also guards the file. A
    failure here must not fail the import that just committed, so it is
    logged and dropped; the next full measure corrects the entry.
    """
    try:
        db.raw_sql("CHECKPOINT")
        entry = measure_table(db, schema, table)
        storage = get_storage()
        storage.setdefault("tables", {})[f"{schema}.{table}"] = entry
        write_storage(storage)
    except Exception:
        frappe.log_error(title=f"Data store: could not measure '{schema}.{table}'")


def forget_table_storage(schema: str, table: str) -> None:
    """Remove a dropped table's entry from `storage.json`.

    The caller holds the warehouse write lock. Never raises: the drop already
    happened, and the next full measure corrects the file.
    """
    try:
        storage = get_storage()
        if storage.get("tables", {}).pop(f"{schema}.{table}", None) is not None:
            write_storage(storage)
    except Exception:
        frappe.log_error(title=f"Data store: could not forget '{schema}.{table}'")


def measure_data_store() -> dict:
    """Measure every table in the warehouse and rewrite `storage.json`.

    The UI reads sizes from the file, never from DuckDB: opening the warehouse
    to look blocks imports for as long as the look takes.
    """
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import CLEANUP_LOCK_TIMEOUT

    path = insights.warehouse.get_db_path()
    with insights.warehouse.get_write_connection(timeout=CLEANUP_LOCK_TIMEOUT) as db:
        # Blocks freed by drops only count as free, and new rows only have
        # blocks, after a checkpoint.
        db.raw_sql("CHECKPOINT")
        tables = db.raw_sql(
            "select schema_name, table_name from duckdb_tables() where database_name = current_database()"
        ).fetchall()
        block_size, free_blocks = db.raw_sql(
            "select block_size, free_blocks from pragma_database_size() "
            "where database_name = current_database()"
        ).fetchone()

        storage = {
            "measured_on": get_datetime_str(now_datetime().replace(microsecond=0)),
            "file_bytes": os.path.getsize(path),
            "block_size": int(block_size),
            "free_bytes": int(free_blocks) * int(block_size),
            "tables": {f"{schema}.{table}": measure_table(db, schema, table) for schema, table in tables},
        }
        write_storage(storage)

    return storage


def enqueue_measure_data_store() -> None:
    frappe.enqueue(
        "insights.insights.doctype.insights_data_source_v3.data_store_storage.measure_data_store",
        queue="long",
        timeout=30 * 60,
        job_id=MEASURE_JOB_ID,
        deduplicate=True,
    )


def is_measuring() -> bool:
    return is_job_enqueued(MEASURE_JOB_ID)


def get_storage() -> dict:
    """The last measurements, or `{}` if the store has never been measured."""
    path = Path(get_storage_path())
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def write_storage(storage: dict) -> None:
    """Replace `storage.json` in one rename, so a reader never sees half a file."""
    path = get_storage_path()
    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix=f".{STORAGE_FILE_NAME}.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(storage, f)
        os.replace(temp_path, path)
    except BaseException:
        with suppress(OSError):
            os.remove(temp_path)
        raise


def get_storage_path() -> str:
    return os.path.join(os.path.dirname(insights.warehouse.get_db_path()), STORAGE_FILE_NAME)


def get_block_size(db: DuckDBBackend) -> int:
    return int(
        db.raw_sql(
            "select block_size from pragma_database_size() where database_name = current_database()"
        ).fetchone()[0]
    )
