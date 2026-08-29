"""The v2 to v3 migrator, as an admin API.

The migrator itself lives in `insights.migrator` and is the only thing that
knows how to convert anything. This module decides who may ask, what a caller
is allowed to name, and where the work runs.

Three things are settled here and nowhere else:

- **No status doctype.** `old_name` on `Insights Query v3`, `Insights Chart v3`
  and `Insights Dashboard v3` already answers "is this v2 dashboard migrated,
  and to what", and the RQ job answers "is it running". A doctype would add a
  third copy of a fact the first two already hold, and a `bench migrate` to
  install it.
- **The write runs on a worker.** A closure is a median of six queries, and a
  bulk selection is however many the admin ticked. `job_id` is derived from the
  dashboard name, so `deduplicate` refuses a second job for a dashboard that
  already has one in flight. `migrate_dashboard`'s own already-migrated skip is
  the second line, not the first: two workers that both passed the skip before
  either wrote would make two workbooks, and only the queue can stop that.
- **v2 is read, never written.** Every read below goes through the migrator's
  own SQL readers or through parameterised SQL of the same shape. Nothing here
  writes a v2 table.
"""

import frappe
from frappe.utils.background_jobs import JobStatus, get_job, is_job_enqueued

from insights.decorators import insights_whitelist
from insights.migrator.v2_workbooks import (
    V2_DASHBOARD,
    V2_DASHBOARD_ITEM,
    V3_DASHBOARD,
    candidate_roots,
    format_report,
    load_v2_dashboard,
    load_v2_queries,
    migrate_dashboard,
    plan_dashboard,
    resolve_v3_data_source,
)

MAX_DASHBOARDS = 50
"""How many dashboards one call may ask for.

A migration is a closure walk, a translation and a workbook write per
dashboard. Fifty is more than any real selection and small enough that a
malformed or hostile list cannot fill the queue.
"""

MAX_LIST_LIMIT = 500

MIGRATION_QUEUE = "long"
MIGRATION_TIMEOUT = 30 * 60


def job_id_for(dashboard: str) -> str:
    return f"insights_v2_migration:{dashboard}"


# -- reading v2 -------------------------------------------------------------


def _existing_v2_dashboards(names) -> set[str]:
    """Which of these names are v2 dashboards.

    By SQL and by parameter, for the same reason the migrator reads that way:
    the site that most needs a migrator has already dropped the v2 code, so its
    `tabInsights Dashboard` rows outlive the doctype the ORM would ask for.
    """
    if not names:
        return set()
    rows = frappe.db.sql(
        f"select name from `tab{V2_DASHBOARD}` where name in %(names)s",
        {"names": tuple(names)},
    )
    return {row[0] for row in rows}


def _v2_dashboard_items(names) -> dict[str, list[dict]]:
    """The items of the named v2 dashboards, grouped by dashboard.

    `select *` for the reason `load_v2_dashboard` gives: the item columns moved
    into `options` at different times on different sites.
    """
    if not names:
        return {}
    rows = frappe.db.sql(
        f"select * from `tab{V2_DASHBOARD_ITEM}` "
        "where parenttype = %(parenttype)s and parent in %(names)s order by idx asc",
        {"parenttype": V2_DASHBOARD, "names": tuple(names)},
        as_dict=True,
    )
    grouped: dict[str, list[dict]] = {name: [] for name in names}
    for row in rows:
        grouped.setdefault(row["parent"], []).append(row)
    return grouped


def _migrated(names) -> dict[str, dict]:
    """The v3 dashboard and workbook each v2 dashboard was migrated into."""
    if not names:
        return {}
    rows = frappe.get_all(
        V3_DASHBOARD,
        filters={"old_name": ["in", list(names)]},
        fields=["name", "workbook", "old_name"],
    )
    return {row.old_name: {"dashboard": row.name, "workbook": row.workbook} for row in rows}


# -- endpoints --------------------------------------------------------------


@insights_whitelist(role="Insights Admin")
def get_v2_dashboards(search: str | None = None, limit: int = 100) -> list[dict]:
    """Every v2 dashboard, with what a migration of it would involve.

    `query_count` counts the queries the items name, not the closure: the
    closure needs a graph walk per dashboard, and the list view wants a size,
    not an exact plan. `preview_v2_dashboard` is where the exact number lives.
    """
    limit = max(1, min(int(limit), MAX_LIST_LIMIT))

    values: dict = {"limit": limit}
    clause = ""
    if search:
        clause = "where title like %(search)s or name like %(search)s"
        values["search"] = f"%{search}%"

    rows = frappe.db.sql(
        f"select name, title, owner, modified from `tab{V2_DASHBOARD}` "
        f"{clause} order by modified desc limit %(limit)s",
        values,
        as_dict=True,
    )

    names = [row["name"] for row in rows]
    items = _v2_dashboard_items(names)
    migrated = _migrated(names)

    dashboards = []
    for row in rows:
        own_items = items.get(row["name"], [])
        landed = migrated.get(row["name"]) or {}
        dashboards.append(
            {
                "name": row["name"],
                "title": row["title"] or row["name"],
                "owner": row["owner"],
                "modified": row["modified"],
                "item_count": len(own_items),
                "query_count": len(candidate_roots(own_items)),
                "migrated_workbook": landed.get("workbook"),
                "migrated_dashboard": landed.get("dashboard"),
            }
        )
    return dashboards


@insights_whitelist(role="Insights Admin")
def preview_v2_dashboard(dashboard: str) -> dict:
    """What migrating this dashboard would produce. Writes nothing.

    The same `plan_dashboard` the write path runs, without the write half. A
    preview that planned differently from the migration would be worse than no
    preview at all, which is why the seam is in the migrator and not here.
    """
    _require_v2_dashboard(dashboard)

    row, items = load_v2_dashboard(dashboard)
    queries = load_v2_queries(candidate_roots(items))
    plan = plan_dashboard(row, items, queries, resolve_data_source=resolve_v3_data_source)

    landed = _migrated([dashboard]).get(dashboard) or {}
    return {
        "dashboard": dashboard,
        "title": plan.title,
        "converts_cleanly": plan.converts_cleanly,
        "counts": {
            "queries": {**plan.kinds, "total": len(plan.queries)},
            "items": {
                "total": plan.item_count,
                "converted": plan.converted_items,
                "dropped": plan.dropped_items,
            },
        },
        "gaps": [
            {
                "origin": origin,
                "kind": gap.kind,
                "source": gap.source,
                "detail": gap.detail,
                "dropped": gap.dropped,
            }
            for origin, gap in plan.all_gaps()
        ],
        "unresolved_data_sources": plan.unresolved_data_sources,
        "dropped_queries": plan.dropped_queries,
        "report": format_report(plan),
        "migrated_workbook": landed.get("workbook"),
        "migrated_dashboard": landed.get("dashboard"),
    }


@insights_whitelist(role="Insights Admin")
def migrate_v2_dashboards(dashboards: list[str]) -> dict:
    """Queue a migration for each named v2 dashboard.

    Returns what it took and what it would not take, so the caller can say why
    a dashboard it selected is missing from the run.
    """
    names = _accepted_names(dashboards)

    existing = _existing_v2_dashboards(names)
    migrated = _migrated(existing)

    accepted: list[str] = []
    skipped: list[dict] = []

    for name in names:
        if name not in existing:
            skipped.append(
                {
                    "dashboard": name,
                    "reason": "not_found",
                    "detail": frappe._("No v2 dashboard answers to this name"),
                }
            )
            continue

        landed = migrated.get(name)
        if landed:
            skipped.append(
                {
                    "dashboard": name,
                    "reason": "already_migrated",
                    "detail": frappe._("Already migrated into workbook {0}").format(landed["workbook"]),
                    **landed,
                }
            )
            continue

        job_id = job_id_for(name)
        if is_job_enqueued(job_id):
            skipped.append(
                {
                    "dashboard": name,
                    "reason": "in_progress",
                    "detail": frappe._("A migration of this dashboard is already running"),
                }
            )
            continue

        frappe.enqueue(
            "insights.api.v2_migration.run_v2_dashboard_migration",
            dashboard=name,
            queue=MIGRATION_QUEUE,
            timeout=MIGRATION_TIMEOUT,
            job_id=job_id,
            deduplicate=True,
        )
        accepted.append(name)

    return {"accepted": accepted, "skipped": skipped}


@insights_whitelist(role="Insights Admin")
def get_v2_migration_status(dashboards: list[str] | None = None) -> dict:
    """Where each named v2 dashboard stands, derived, not stored.

    `old_name` settles a finished migration for good. The queue settles the rest
    and forgets: RQ expires a finished job's record, so a dashboard whose job
    failed long enough ago reads as `not_started` again. That is the truthful
    answer - nothing is holding the failure any more - and re-running is the
    only way to learn more.
    """
    if dashboards is None:
        names = list(
            frappe.db.sql_list(f"select name from `tab{V2_DASHBOARD}` order by modified desc limit 500")
        )
    else:
        names = _accepted_names(dashboards)

    migrated = _migrated(names)

    status = {}
    for name in names:
        landed = migrated.get(name)
        if landed:
            status[name] = {
                "status": "migrated",
                "workbook": landed["workbook"],
                "dashboard": landed["dashboard"],
                "error": None,
            }
            continue
        status[name] = {"workbook": None, "dashboard": None, **_job_state(job_id_for(name))}
    return status


# -- the job ----------------------------------------------------------------


def run_v2_dashboard_migration(dashboard: str) -> dict:
    """Migrate one v2 dashboard. The worker's entry point.

    Not whitelisted: it is reached through the queue, and `migrate_v2_dashboards`
    is the only thing that puts it there. It re-checks the dashboard exists
    because a job outlives the request that queued it.
    """
    if not _existing_v2_dashboards([dashboard]):
        frappe.throw(frappe._("Dashboard {0} not found").format(dashboard))

    result = migrate_dashboard(dashboard)
    return {
        "dashboard": result.dashboard,
        "workbook": result.workbook,
        "skipped": result.skipped,
        "report": result.report,
    }


# -- helpers ----------------------------------------------------------------


def _accepted_names(dashboards) -> list[str]:
    """The caller's list, deduplicated in order, bounded, and all strings."""
    if not dashboards:
        frappe.throw(frappe._("Name at least one dashboard"))

    if len(dashboards) > MAX_DASHBOARDS:
        frappe.throw(
            frappe._("Migrate at most {0} dashboards at a time, not {1}").format(
                MAX_DASHBOARDS, len(dashboards)
            )
        )

    names: list[str] = []
    for name in dashboards:
        if not isinstance(name, str) or not name.strip():
            frappe.throw(frappe._("A dashboard name must be a non-empty string"))
        name = name.strip()
        if name not in names:
            names.append(name)
    return names


def _require_v2_dashboard(dashboard: str) -> None:
    if not _existing_v2_dashboards([dashboard]):
        frappe.throw(frappe._("Dashboard {0} not found").format(dashboard))


def _job_state(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        return {"status": "not_started", "error": None}

    rq_status = job.get_status(refresh=False)
    if rq_status in (JobStatus.CREATED, JobStatus.QUEUED, JobStatus.DEFERRED, JobStatus.SCHEDULED):
        return {"status": "queued", "error": None}
    if rq_status == JobStatus.STARTED:
        return {"status": "in_progress", "error": None}
    if rq_status in (JobStatus.FAILED, JobStatus.STOPPED, JobStatus.CANCELED):
        return {"status": "failed", "error": _last_line(job.exc_info)}
    # Finished, and yet no v3 dashboard carries this `old_name`: the write half
    # never ran. Only re-running can say more than that.
    return {
        "status": "failed",
        "error": frappe._("The migration finished without creating a dashboard"),
    }


def _last_line(exc_info) -> str | None:
    if not exc_info:
        return None
    lines = [line for line in str(exc_info).strip().splitlines() if line.strip()]
    return lines[-1] if lines else None
