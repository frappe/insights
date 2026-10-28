from datetime import datetime

import frappe
from croniter import croniter
from frappe.query_builder.functions import Max
from frappe.utils import add_to_date, cint, flt, now, now_datetime
from frappe.utils.background_jobs import get_job_status
from frappe.utils.synchronization import filelock
from rq.job import JobStatus

import insights
from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.data_warehouse import IMPORT_TIMEOUT, import_job_id
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

# An import holds a chunk of rows and then its commit in memory, and every worker
# on the long queue would take one, so a site runs only this many at once.
MAX_RUNNING_IMPORTS = 2


def _bounded(value, lo, hi, cast=cint):
    """Keep a caller's number inside what one request may ask for."""
    try:
        return max(lo, min(cast(value), hi))
    except (TypeError, ValueError):
        return lo


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
    """Import each stored table whose sync schedule is due, a few at a time.

    Runs on every scheduler tick, and as each import ends, so the next due table
    need not wait for the tick. Due counts from the table's newest import start,
    not its last success, so a failing table waits for its next due time instead
    of retrying on every tick.
    """
    # the tick and an import that ends can count the running imports at once
    with filelock("insights_sync_tables"):
        tables = frappe.get_all(
            "Insights Table v3",
            filters={"stored": 1},
            fields=["data_source", "table", "sync_schedule", "creation"],
        )
        now = now_datetime()
        running = count_running_imports(tables, now)
        if running >= MAX_RUNNING_IMPORTS:
            return

        Log = frappe.qb.DocType("Insights Table Import Log")
        started = {
            (row.data_source, row.table_name): row.started_at
            for row in frappe.qb.from_(Log)
            .select(Log.data_source, Log.table_name, Max(Log.started_at).as_("started_at"))
            .groupby(Log.data_source, Log.table_name)
            .run(as_dict=True)
        }

        due = []
        for table in tables:
            last = started.get((table.data_source, table.table)) or table.creation
            try:
                due_at = croniter(table.sync_schedule, last).get_next(datetime)
            except Exception:
                frappe.log_error(title=f"Error scheduling import of {table.table}")
                continue
            if due_at <= now:
                due.append((due_at, table))

        # the table that has waited longest goes first, or a table could wait for good
        for _, table in sorted(due, key=lambda item: item[0]):
            if running >= MAX_RUNNING_IMPORTS:
                break
            try:
                # an import already queued or running is counted already
                if not insights.warehouse.get_table(table.data_source, table.table).enqueue_import():
                    running += 1
            except Exception:
                frappe.log_error(title=f"Error scheduling import of {table.table}")


def import_queued(data_source: str, table_name: str) -> bool:
    return get_job_status(import_job_id(data_source, table_name)) == JobStatus.QUEUED


def count_running_imports(tables: list, now: datetime) -> int:
    """Imports started within their job's timeout that have not ended, then queued ones.

    A worker killed mid-import never ends its log, so a log older than the
    timeout no longer holds a place. A queued import has written no log yet.
    """
    running = frappe.db.count(
        "Insights Table Import Log",
        {
            "status": "In Progress",
            "ended_at": ("is", "not set"),
            "started_at": ("between", [add_to_date(now, seconds=-IMPORT_TIMEOUT), now]),
        },
    )
    for table in tables:
        if running >= MAX_RUNNING_IMPORTS:
            break
        running += import_queued(table.data_source, table.table)
    return running


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

    for name in logs:
        log = frappe.get_doc("Insights Table Import Log", name)
        log.status = "Failed"
        # a killed worker runs no handler, so the log would not say why it failed
        log.log_output(
            f"[{now()}] The import stopped without finishing: its worker was killed or restarted, "
            "for example when the server ran out of memory."
        )


@insights_whitelist(role="Insights Admin", methods=["POST"])
def profile_warehouse(
    limit: int = 5,
    since_days: int = 7,
    min_time: float = 1.0,
    concurrency: int = 1,
    max_seconds: int = 30,
    budget: int = 60,
):
    """Profile the slowest data store queries and answer with the report.

    For an operator with no shell on the host: the same profile that
    `insights.warehouse_profile.run` prints from the bench, as JSON.

    Each replay runs its query for real, so this call holds the worker it runs
    in. `budget` bounds that: once it is spent no further query is started, and
    `not_profiled` names what was left for the next call. The arguments are
    held to what one request may ask for — a longer profile belongs on the
    bench, which nothing here times out.

    Args:
        limit: How many of the slowest distinct queries to replay (1-20).
        since_days: How far back to read the execution log (1-90).
        min_time: Ignore queries already faster than this, in seconds.
        concurrency: Replay each statement this many times at once (1-4).
        max_seconds: Cancel a single replay after this long (5-60).
        budget: Start no new replay once this many seconds have passed (10-120).
    """
    from insights.warehouse_profile import build_report

    return build_report(
        limit=_bounded(limit, 1, 20),
        since_days=_bounded(since_days, 1, 90),
        min_time=_bounded(min_time, 0, 3600, cast=flt),
        concurrency=_bounded(concurrency, 1, 4),
        max_seconds=_bounded(max_seconds, 5, 60),
        budget=_bounded(budget, 10, 120),
    )
