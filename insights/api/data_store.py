import os
from datetime import datetime

import frappe
from croniter import croniter
from frappe.query_builder.functions import Max
from frappe.utils import now_datetime

import insights
from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3 import data_store_storage
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    LEFTOVER_TABLE_PREFIX,
    UNUSED_TABLE_DAYS,
    execution_log_covers_unused_window,
    get_last_execution_per_table,
    get_unused_tables,
    get_warehouse_schema_name,
)
from insights.insights.doctype.insights_table_v3.column_usage import get_column_readers_by_table
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    get_skipped_columns,
    get_sync_columns,
    get_table_name,
)


@insights_whitelist()
def get_data_store_tables(data_source: str | None = None, search_term: str | None = None, limit: int = 100):
    filters = {"stored": 1}
    if data_source:
        filters["data_source"] = data_source
    or_filters = (
        {"label": ["like", f"%{search_term}%"], "table": ["like", f"%{search_term}%"]}
        if search_term
        else None
    )
    # get_list applies get_permission_query_conditions, keeping tables scoped to the caller
    tables = frappe.get_list(
        "Insights Table v3",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "table", "label", "data_source", "last_synced_on"],
        limit=limit,
    )
    database_types = {
        d.name: d.database_type
        for d in frappe.get_all(
            "Insights Data Source v3",
            filters={"name": ["in", list({t.data_source for t in tables})]},
            fields=["name", "database_type"],
        )
    }

    ret = []
    for table in tables:
        ret.append(
            frappe._dict(
                {
                    "name": table.name,
                    "label": table.label,
                    "table_name": table.table,
                    "data_source": table.data_source,
                    "database_type": database_types.get(table.data_source),
                    "last_synced_on": table.last_synced_on,
                }
            )
        )
    return ret


@insights_whitelist(role="Insights Admin", methods=["POST"])
def import_table(data_source: str, table_name: str):
    name = get_table_name(data_source, table_name)
    table_doc = frappe.get_doc("Insights Table v3", name)
    table_doc.import_to_warehouse()


def sync_tables():
    """Import each stored table whose sync schedule is due.

    Runs on every scheduler tick. Due counts from the table's newest import start,
    not its last success, so a failing table waits for its next due time instead
    of retrying on every tick.
    """
    tables = frappe.get_all(
        "Insights Table v3",
        filters={"stored": 1},
        fields=["data_source", "table", "sync_schedule", "creation"],
    )

    Log = frappe.qb.DocType("Insights Table Import Log")
    started = {
        (row.data_source, row.table_name): row.started_at
        for row in frappe.qb.from_(Log)
        .select(Log.data_source, Log.table_name, Max(Log.started_at).as_("started_at"))
        .groupby(Log.data_source, Log.table_name)
        .run(as_dict=True)
    }

    now = now_datetime()
    for table in tables:
        last = started.get((table.data_source, table.table)) or table.creation
        try:
            if croniter(table.sync_schedule, last).get_next(datetime) <= now:
                import_table(table.data_source, table.table)
        except Exception:
            frappe.log_error(title=f"Error scheduling import of {table.table}")


def update_failed_sync_status():
    from frappe.query_builder import Interval
    from frappe.query_builder.functions import Now

    Log = frappe.qb.DocType("Insights Table Import Log")
    logs = frappe.db.get_values(
        Log,
        ((Log.status == "In Progress") & (Log.creation < (Now() - Interval(hours=1)))),
        pluck="name",
    )

    if not logs:
        return

    for log in logs:
        frappe.db.set_value("Insights Table Import Log", log, "status", "Failed")


@insights_whitelist(role="Insights Admin")
def get_storage():
    """Where the Data Store's disk goes, from the last measure.

    Sizes come from `storage.json`, never from DuckDB: opening the file to
    look blocks imports. Every byte of the file lands in one group, so the
    groups sum to `file_bytes`. The measure lags the file, so `other` is what
    is left over, and stays at zero rather than going negative.
    """
    storage = data_store_storage.get_storage()
    measured = storage.get("tables") or {}
    path = insights.warehouse.get_db_path()
    file_bytes = os.path.getsize(path) if os.path.exists(path) else 0
    usage_known = execution_log_covers_unused_window()

    docs = frappe.get_all(
        "Insights Table v3",
        filters={"stored": 1},
        fields=[
            "name",
            "data_source",
            "table",
            "label",
            "sync_mode",
            "sync_strategy",
            "sync_cursor_column",
            "sync_primary_key_column",
            "skipped_columns",
        ],
    )
    entries = {
        doc.name: entry
        for doc in docs
        if (entry := measured.get(f"{get_warehouse_schema_name(doc.data_source)}.{frappe.scrub(doc.table)}"))
    }
    docs = [doc for doc in docs if doc.name in entries]

    readers = get_column_readers_by_table(
        {(doc.data_source, doc.table): list(entries[doc.name]["columns"]) for doc in docs}
    )
    last_read = get_last_execution_per_table()
    unused = (
        get_unused_tables({(doc.data_source, doc.table) for doc in docs}, last_read) if usage_known else set()
    )

    groups = dict.fromkeys(("read", "unread_columns", "unread_tables", "leftover", "other", "free"), 0)
    tables = []
    for doc in docs:
        entry = entries[doc.name]
        key = (doc.data_source, doc.table)
        last_read_on = last_read.get(key)
        skipped = set(get_skipped_columns(doc))
        sync_columns = get_sync_columns(doc)

        columns = [
            {
                "name": name,
                "bytes": size,
                "readers": readers[key][name],
                "skipped": name in skipped,
                "skippable": name not in sync_columns,
            }
            for name, size in sorted(entry["columns"].items(), key=lambda column: -column[1])
        ]

        unread = key in unused
        if unread:
            groups["unread_tables"] += entry["bytes"]
        else:
            for column in columns:
                # the sync reads its cursor and key, so they are in use without a reader
                in_use = column["readers"] or not column["skippable"]
                groups["read" if in_use else "unread_columns"] += column["bytes"]

        tables.append(
            {
                "name": doc.name,
                "data_source": doc.data_source,
                "table": doc.table,
                "label": doc.label,
                "sync_mode": doc.sync_mode,
                "bytes": entry["bytes"],
                "rows": entry["rows"],
                "measured_on": entry["measured_on"],
                "last_read_on": last_read_on,
                "unread": unread,
                "columns": columns,
            }
        )

    leftover_tables = []
    for qualified, entry in measured.items():
        schema, _, table = qualified.partition(".")
        if table.startswith(LEFTOVER_TABLE_PREFIX):
            leftover_tables.append({"schema": schema, "table": table, "bytes": entry["bytes"]})
            groups["leftover"] += entry["bytes"]

    used = sum(groups.values())
    groups["free"] = min(storage.get("free_bytes") or 0, max(file_bytes - used, 0))
    groups["other"] = max(file_bytes - used - groups["free"], 0)

    return {
        "measured_on": storage.get("measured_on"),
        "measuring": data_store_storage.is_measuring(),
        "file_bytes": file_bytes,
        "free_bytes": storage.get("free_bytes"),
        "unread_days": UNUSED_TABLE_DAYS,
        "usage_known": usage_known,
        "cleanup": get_cleanup_state(),
        "groups": groups,
        "tables": sorted(tables, key=lambda table: -table["bytes"]),
        "leftover_tables": sorted(leftover_tables, key=lambda table: -table["bytes"]),
    }


@insights_whitelist(role="Insights Admin", methods=["POST"])
def resume_cleanup():
    if job := get_cleanup_job():
        frappe.db.set_value("Scheduled Job Type", job.name, "stopped", 0)


@insights_whitelist(role="Insights Admin", methods=["POST"])
def measure():
    data_store_storage.enqueue_measure_data_store()


def get_cleanup_job():
    return frappe.db.get_value(
        "Scheduled Job Type",
        {"method": ["like", "%.cleanup_data_store"]},
        ["name", "stopped", "last_execution", "modified"],
        as_dict=True,
    )


def get_cleanup_state() -> dict:
    """A stopped job is stopped by an edit, so its `modified` is when it stopped."""
    job = get_cleanup_job()
    if not job:
        return {"stopped": False, "stopped_on": None, "last_run": None}
    return {
        "stopped": bool(job.stopped),
        "stopped_on": job.modified if job.stopped else None,
        "last_run": job.last_execution,
    }
