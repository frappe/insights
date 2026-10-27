from datetime import datetime

import frappe
from croniter import croniter
from frappe.query_builder.functions import Max
from frappe.utils import add_to_date, now, now_datetime

import insights
from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.data_warehouse import IMPORT_TIMEOUT
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

# An import holds a chunk of rows and then its commit in memory, and every worker
# on the long queue would take one, so a site runs only this many at once.
MAX_RUNNING_IMPORTS = 2


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
    running = count_running_imports(now)
    for table in tables:
        if running >= MAX_RUNNING_IMPORTS:
            break
        last = started.get((table.data_source, table.table)) or table.creation
        try:
            if croniter(table.sync_schedule, last).get_next(datetime) <= now:
                # a table whose import is already queued counts as running too
                insights.warehouse.get_table(table.data_source, table.table).enqueue_import()
                running += 1
        except Exception:
            frappe.log_error(title=f"Error scheduling import of {table.table}")


def count_running_imports(now: datetime) -> int:
    """Imports started within their job's timeout that have not ended.

    A worker killed mid-import never ends its log, so a log older than the
    timeout no longer holds a place.
    """
    return frappe.db.count(
        "Insights Table Import Log",
        {
            "status": "In Progress",
            "ended_at": ("is", "not set"),
            "started_at": ("between", [add_to_date(now, seconds=-IMPORT_TIMEOUT), now]),
        },
    )


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
