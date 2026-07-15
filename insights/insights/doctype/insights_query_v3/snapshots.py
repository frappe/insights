# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Materialized query snapshots.

A materialized query is executed once against its live source in a background
job and its *result* (not the source rows) is stored as a table in the DuckDB
warehouse. Charts and downstream queries then read the stored result instead of
re-running the expensive live query on every view.

Because we store the query result — already aggregated down to its final grain —
there is no incremental sync state to keep consistent: each refresh recomputes
from scratch and replaces the table, so source deletes/updates can never leave a
stale row behind. The trade-off is staleness, surfaced to the user as an
"as of <time>" label.
"""

from contextlib import suppress

import frappe

import insights

# Dedicated DuckDB schema so snapshot tables never collide with imported
# data-source tables (which live in per-data-source schemas).
SNAPSHOT_SCHEMA = "query_snapshots"

# Snapshots are meant for aggregated results. This is a safety net against a
# user materializing a per-row query whose result is as large as the source.
MAX_SNAPSHOT_ROWS = 1_000_000

REFRESH_INTERVAL_HOURS = {"Hourly": 1, "Daily": 24}


class SnapshotTooLargeError(frappe.ValidationError):
    pass


def snapshot_table_name(query_name: str) -> str:
    return frappe.scrub(query_name)


def snapshot_exists(query_name: str) -> bool:
    try:
        insights.warehouse.db.table(snapshot_table_name(query_name), database=SNAPSHOT_SCHEMA)
        return True
    except Exception:
        return False


def get_snapshot_table(query_name: str):
    return insights.warehouse.db.table(snapshot_table_name(query_name), database=SNAPSHOT_SCHEMA)


def compute_operations_digest(operations) -> str:
    from insights.cache_utils import make_digest

    return make_digest(frappe.as_json(frappe.parse_json(operations) or []))


def enqueue_snapshot_refresh(query_name: str, now: bool = False) -> None:
    frappe.enqueue(
        "insights.insights.doctype.insights_query_v3.snapshots.refresh_snapshot",
        queue="long",
        query_name=query_name,
        now=now or bool(frappe.flags.in_test),
        enqueue_after_commit=True,
        job_id=f"insights-snapshot-refresh-{query_name}",
        deduplicate=True,
    )


def refresh_snapshot(query_name: str) -> None:
    doc = frappe.get_doc("Insights Query v3", query_name)
    if not doc.is_materialized:
        return

    _set_snapshot_state(doc, snapshot_status="Running", snapshot_error="")
    try:
        # resolve_snapshot=False so we build against the live source rather than
        # reading (and rewriting) this query's own stale snapshot.
        ibis_query = doc.build(resolve_snapshot=False)
        _disable_source_timeout(ibis_query)

        from insights.insights.doctype.insights_data_source_v3.ibis_utils import execute_ibis_query

        # Bound memory: pull at most one row past the cap so we can detect (and
        # reject) an oversized result instead of loading millions of rows.
        capped = ibis_query.limit(MAX_SNAPSHOT_ROWS + 1)
        df, _time_taken = execute_ibis_query(capped, paginate=False, cache=False)

        if len(df) > MAX_SNAPSHOT_ROWS:
            raise SnapshotTooLargeError(
                f"Query result exceeds the {MAX_SNAPSHOT_ROWS:,} row snapshot limit. "
                "Materialization is meant for aggregated results — add a summarize step."
            )

        _write_snapshot(query_name, df, ibis_query.schema())

        _set_snapshot_state(
            doc,
            snapshot_status="Completed",
            snapshot_error="",
            snapshot_row_count=len(df),
            snapshot_last_refreshed_at=frappe.utils.now(),
            snapshot_digest=compute_operations_digest(doc.operations),
        )
    except Exception as e:
        # Keep the previous snapshot; a failed refresh must never fall back to
        # live execution on the read path (that would reintroduce the load spike
        # this feature exists to remove).
        _set_snapshot_state(doc, snapshot_status="Failed", snapshot_error=str(e)[:2000])
        raise


def drop_snapshot(query_name: str) -> None:
    with insights.warehouse.get_write_connection(SNAPSHOT_SCHEMA) as db:
        with suppress(Exception):
            db.drop_table(snapshot_table_name(query_name), force=True)


def refresh_due_snapshots() -> None:
    """Scheduler entry point: enqueue a refresh for every materialized query
    whose snapshot is older than its configured frequency."""
    now = frappe.utils.now_datetime()
    queries = frappe.get_all(
        "Insights Query v3",
        filters={"is_materialized": 1},
        fields=[
            "name",
            "snapshot_refresh_frequency",
            "snapshot_last_refreshed_at",
            "snapshot_status",
        ],
    )
    for q in queries:
        if q.snapshot_status in ("Queued", "Running"):
            continue
        if _is_snapshot_due(q, now):
            enqueue_snapshot_refresh(q.name)


def _is_snapshot_due(query, now) -> bool:
    if not query.snapshot_last_refreshed_at:
        return True
    elapsed_hours = (now - frappe.utils.get_datetime(query.snapshot_last_refreshed_at)).total_seconds() / 3600
    interval = REFRESH_INTERVAL_HOURS.get(query.snapshot_refresh_frequency or "Daily", 24)
    return elapsed_hours >= interval


def _write_snapshot(query_name: str, df, schema) -> None:
    with insights.warehouse.get_table_writer(
        snapshot_table_name(query_name),
        schema,
        database=SNAPSHOT_SCHEMA,
        mode="replace",
    ) as writer:
        writer.insert(df)


def _disable_source_timeout(ibis_query) -> None:
    """Refreshes are long-running background jobs, so the interactive
    max_execution_time must not apply. Mirror the import path, which lifts the
    statement timeout on its dedicated worker connection."""
    backend = ibis_query.get_backend()
    if backend is None:
        return
    with suppress(Exception):
        backend.raw_sql("SET MAX_STATEMENT_TIME=0")


def _set_snapshot_state(doc, **values) -> None:
    # db_set (not save) so we don't re-trigger on_update / churn modified.
    doc.db_set(values, commit=True, update_modified=False)
