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
- **A verification is stored in global defaults, not in a doctype.** The same
  reason a status doctype was refused: a `tabDefaultValue` row needs no
  `bench migrate`, and the outcome is a per-dashboard note, not a document
  anybody lists, links to or edits.

The page in front of this asks one question - "what happens to my dashboard" -
so the reading endpoints answer per named item, not per gap kind.
"""

import collections
import json
from contextlib import suppress

import frappe
from frappe.utils import add_days, get_datetime, now_datetime
from frappe.utils.background_jobs import JobStatus, get_job, is_job_enqueued
from frappe.utils.telemetry import capture

from insights.decorators import has_role, insights_whitelist
from insights.migrator.v2_charts import chart_from_dashboard_item, parse_json
from insights.migrator.v2_dashboards import FILTER_ITEM, TEXT_ITEM
from insights.migrator.v2_verification import DIFFERENT, EXPECTED, SAME, verify_migration
from insights.migrator.v2_workbooks import (
    V2_DASHBOARD,
    V2_DASHBOARD_ITEM,
    V2_QUERY,
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

# The one place the gate is named. `_can_migrate` answers the same test, so
# the nudge cannot offer a button the endpoints refuse.
MIGRATION_ROLE = "Insights Admin"

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


def _v2_installed() -> bool:
    """Whether this site holds v2 dashboards at all.

    A fresh v3 install never had the table, and a site that dropped the v2 app
    kept its rows. Both are normal, and neither is an error worth raising at a
    caller that only wants a count.
    """
    return bool(frappe.db.table_exists(V2_DASHBOARD))


# -- what a migration does to each named thing ------------------------------

CHART_ITEM = "chart"


def _item_title(item: dict) -> str:
    """What the user calls this dashboard item.

    Empty for a text box and for a chart nobody titled; the reader supplies the
    word, because a fallback title is a label and labels are translated there.
    """
    if item.get("item_type") == TEXT_ITEM:
        return ""
    options = parse_json(item.get("options"))
    if item.get("item_type") == FILTER_ITEM:
        return item.get("filter_label") or options.get("label") or ""
    return chart_from_dashboard_item(item).get("title") or ""


def _item_kind(item: dict) -> str:
    item_type = item.get("item_type")
    if item_type == TEXT_ITEM:
        return "text"
    if item_type == FILTER_ITEM:
        return "filter"
    return CHART_ITEM


def _note(gap, query: str = "") -> dict:
    return {
        "kind": gap.kind,
        "source": gap.source,
        "detail": gap.detail,
        "dropped": gap.dropped,
        "query": query,
    }


def _findings(plan, items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Everything the plan found, hung off the item it happens to.

    A gap knows its kind and the docname that raised it. The user knows "Top
    Customers". This is the one place the two are joined, and it is here rather
    than in the migrator because the migrator has no reader to answer to.

    A query gap reaches the charts that read that query, because that is where
    the user sees it. A query nothing charts directly - a Query Store reference
    a chart reaches through another query - keeps its own entry.
    """
    charts = {chart.source: chart for chart in (plan.dashboard.charts if plan.dashboard else [])}
    orphans = set(plan.orphan_items)

    by_item: dict[str, list[dict]] = {}
    for origin, gap in plan.all_gaps():
        if origin in ("item", "dashboard") and str(gap.source) in {str(i.get("name")) for i in items}:
            by_item.setdefault(str(gap.source), []).append(_note(gap))

    query_titles = {p.source: p.title for p in plan.queries}
    charted_by_query: dict[str, list[str]] = {}
    for item in items:
        query = chart_from_dashboard_item(item).get("query")
        if query:
            charted_by_query.setdefault(query, []).append(str(item.get("name")))

    query_sections: list[dict] = []
    for query_plan in plan.queries:
        notes = [
            _note(gap, query=query_titles.get(query_plan.source, query_plan.source))
            for gap in query_plan.translated.gaps
        ]
        if not notes:
            continue
        readers = charted_by_query.get(query_plan.source) or []
        if readers:
            for key in readers:
                by_item.setdefault(key, []).extend(notes)
        else:
            query_sections.append(
                {
                    "query": query_plan.source,
                    "title": query_plan.title,
                    "notes": notes,
                }
            )

    reported: list[dict] = []
    for item in items:
        key = str(item.get("name"))
        kind = _item_kind(item)
        chart = charts.get(item.get("name"))
        dropped = key in orphans or (kind == CHART_ITEM and chart is not None and not chart.chart_type)
        notes = by_item.get(key, [])
        reported.append(
            {
                "key": key,
                "title": _item_title(item),
                "kind": kind,
                "state": "dropped" if dropped else ("changed" if notes else "ok"),
                "notes": notes,
            }
        )

    # A dashboard-level gap belongs to no item - `public_not_carried` is the one
    # in production - so it rides in a section of its own rather than vanishing.
    loose = [
        _note(gap)
        for origin, gap in plan.all_gaps()
        if origin == "dashboard" and str(gap.source) not in {i["key"] for i in reported}
    ]
    if loose:
        query_sections.insert(0, {"query": "", "title": "", "notes": loose})

    return reported, query_sections


def _verdict(plan, migrated: bool) -> str:
    if migrated:
        return "migrated"
    if plan.converts_cleanly and not plan.all_gaps():
        return "ready"
    return "review"


def _summarize(plan, items: list[dict], landed: dict) -> dict:
    """One dashboard's whole answer, in the shape the page reads it."""
    reported, query_sections = _findings(plan, items)
    charts = [item for item in reported if item["kind"] == CHART_ITEM]

    return {
        "dashboard": plan.source,
        "title": plan.title,
        "verdict": _verdict(plan, bool(landed)),
        "converts_cleanly": plan.converts_cleanly,
        "chart_count": len(charts),
        "charts_carried": len([item for item in charts if item["state"] != "dropped"]),
        "items": reported,
        "queries": query_sections,
        "counts": {
            "queries": {**plan.kinds, "total": len(plan.queries)},
            "items": {
                "total": plan.item_count,
                "converted": plan.converted_items,
                "dropped": plan.dropped_items,
            },
        },
        "unresolved_data_sources": plan.unresolved_data_sources,
        "dropped_queries": plan.dropped_queries,
        "report": format_report(plan),
        "migrated_workbook": landed.get("workbook"),
        "migrated_dashboard": landed.get("dashboard"),
        # Carried on the scan rather than fetched per row: the reader shows it
        # beside the verdict, and asking again per dashboard is a round trip per
        # row for something this call already knows.
        "verification": _verification_summary(read_verification(plan.source)) if landed else None,
    }


def _plan_for(dashboard: str):
    row, items = load_v2_dashboard(dashboard)
    queries = load_v2_queries(candidate_roots(items))
    plan = plan_dashboard(row, items, queries, resolve_data_source=resolve_v3_data_source)
    return plan, items


# -- telemetry --------------------------------------------------------------
#
# The browser reports intent - a nudge clicked, a page opened, a dashboard read.
# This module reports outcome, because an outcome is made on a worker and the
# admin who started it may have closed the page long before it lands. A migrator
# that only reported when somebody watched would flatter itself.
#
# Nothing here carries a dashboard title, a query name, a column or an error
# message. Every property is a count, a verdict, or a gap kind - fixed strings
# this repo wrote, and the same vocabulary the page shows the user.


def _capture(event: str, properties: dict, interval: str | None = None) -> None:
    """Telemetry must never be the reason a migration fails."""
    with suppress(Exception):
        capture(event, "insights", properties=properties, interval=interval)


def _gap_kinds(plan) -> list[str]:
    """The distinct gap kinds one plan hit, sorted.

    The kinds and not the count per kind: what a fleet report answers is "which
    gap does the migrator still not cover", and one dashboard hitting `sql_floor`
    forty times is the same answer as hitting it once.
    """
    return sorted({gap.kind for _, gap in plan.all_gaps()})


# -- endpoints --------------------------------------------------------------


@insights_whitelist(role=MIGRATION_ROLE)
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


@insights_whitelist(role=MIGRATION_ROLE)
def preview_v2_dashboard(dashboard: str) -> dict:
    """What migrating this dashboard would produce. Writes nothing.

    The same `plan_dashboard` the write path runs, without the write half. A
    preview that planned differently from the migration would be worse than no
    preview at all, which is why the seam is in the migrator and not here.
    """
    _require_v2_dashboard(dashboard)

    plan, items = _plan_for(dashboard)
    return _summarize(plan, items, _migrated([dashboard]).get(dashboard) or {})


SCAN_CACHE_KEY = "insights_v2_migration_scan"
SCAN_CACHE_TTL = 30 * 60
SCAN_JOB_ID = "insights_v2_migration_scan"


@insights_whitelist(role=MIGRATION_ROLE)
def scan_v2_dashboards(refresh: bool = False) -> dict:
    """The triage of every v2 dashboard, or a promise that one is being built.

    Planning one dashboard is a closure walk and a translation, and this reads
    every dashboard on the site, so the work runs on a worker and the answer is
    cached. The caller polls this same endpoint until `status` is `ready`.

    A refresh keeps serving the rows it has while the new ones are built. The
    page then dims instead of emptying, which is what an admin who just
    migrated something is looking at.
    """
    if not _v2_installed():
        return {"available": False, "status": "ready", "dashboards": [], "scanned_at": None}

    cached = frappe.cache().get_value(SCAN_CACHE_KEY)
    if cached and not refresh:
        return cached

    if not is_job_enqueued(SCAN_JOB_ID):
        frappe.enqueue(
            "insights.api.v2_migration.run_v2_dashboard_scan",
            queue=MIGRATION_QUEUE,
            timeout=MIGRATION_TIMEOUT,
            job_id=SCAN_JOB_ID,
            deduplicate=True,
        )

    stale = cached or {}
    return {
        "available": True,
        "status": "scanning",
        "dashboards": stale.get("dashboards", []),
        "scanned_at": stale.get("scanned_at"),
    }


def run_v2_dashboard_scan() -> dict:
    """Build the triage and cache it.

    Not whitelisted: it is reached through the queue, and `scan_v2_dashboards`
    is the gate in front of it.
    """
    try:
        scan = _build_scan()
    except Exception:
        frappe.log_error("v2 migration scan failed")
        scan = {
            "available": True,
            "status": "failed",
            "dashboards": [],
            "scanned_at": frappe.utils.now(),
            "error": frappe._("The scan could not be built. Check the error log."),
        }

    # Cached even when it failed, so the page stops asking. `refresh` is how the
    # admin says to try again.
    frappe.cache().set_value(SCAN_CACHE_KEY, scan, expires_in_sec=SCAN_CACHE_TTL)
    return scan


def _build_scan() -> dict:
    rows = frappe.db.sql(
        f"select name from `tab{V2_DASHBOARD}` order by modified desc limit %(limit)s",
        {"limit": MAX_LIST_LIMIT},
        as_dict=True,
    )
    migrated = _migrated([row["name"] for row in rows])

    dashboards = []
    for row in rows:
        name = row["name"]
        try:
            plan, items = _plan_for(name)
            dashboards.append(_summarize(plan, items, migrated.get(name) or {}))
        except Exception:
            # One unreadable dashboard must not cost the user the other 40. The
            # row still appears, saying the only true thing about it.
            frappe.log_error(f"v2 migration scan failed for {name}")
            dashboards.append(_unreadable(name, migrated.get(name) or {}))

    scan = {
        "available": True,
        "status": "ready",
        "dashboards": dashboards,
        "scanned_at": frappe.utils.now(),
    }

    # The shape of one site's v2 estate, which nothing else reports. Only on a
    # real scan - a cache hit never reaches here - and once a day, because an
    # estate changes far more slowly than an admin reloads the page.
    verdicts = collections.Counter(d["verdict"] for d in dashboards)
    _capture(
        "v2_migration_scanned",
        {
            "dashboards": len(dashboards),
            "ready": verdicts["ready"],
            "review": verdicts["review"],
            "migrated": verdicts["migrated"],
            "unreadable": verdicts["unreadable"],
        },
        interval="1d",
    )
    return scan


def _unreadable(name: str, landed: dict) -> dict:
    title = frappe.db.sql(f"select title from `tab{V2_DASHBOARD}` where name = %s", (name,))
    return {
        "dashboard": name,
        "title": (title and title[0][0]) or name,
        "verdict": "migrated" if landed else "unreadable",
        "converts_cleanly": False,
        "chart_count": 0,
        "charts_carried": 0,
        "items": [],
        "queries": [],
        "counts": {},
        "unresolved_data_sources": [],
        "dropped_queries": [],
        "report": "",
        "migrated_workbook": landed.get("workbook"),
        "migrated_dashboard": landed.get("dashboard"),
        "verification": _verification_summary(read_verification(name)) if landed else None,
    }


# -- the nudge --------------------------------------------------------------

V2_ACTIVE_WITHIN_DAYS = 180
"""How long after its last use v2 still counts as live.

Long, because the window is not a guess at how often people work - it is how
long a team keeps the intent to bring their old dashboards over. A team that
has not opened v2 in half a year has been living without those dashboards, and
a banner will not change that.
"""

NUDGE_HIDDEN_KEY = "insights_v2_migration_nudge_hidden"


def _v2_last_used() -> str | None:
    """When anybody last ran or edited a v2 query.

    `last_execution` is written on every fetch, and a dashboard view fetches
    through a cache that holds for minutes, so a team reading v2 daily writes
    it daily. `modified` catches a team that edits without running. Neither
    alone is the signal, so the answer is the later of the two.
    """
    if not frappe.db.table_exists(V2_QUERY):
        return None
    rows = frappe.db.sql(
        f"select max(greatest(coalesce(last_execution, modified), modified)) " f"from `tab{V2_QUERY}`"
    )
    return rows[0][0] if rows else None


def _v2_dashboards_waiting() -> int:
    """How many v2 dashboards are still worth offering.

    Not every v2 row: one already migrated is done, and one holding no chart
    carries nothing across. Counting those makes the banner promise work that
    is not there. The migration page still lists them, and says of each that it
    has no charts to carry over - that is the page's job, and not a number's.
    """
    if not _v2_installed():
        return 0
    return frappe.db.sql(
        f"""
        select count(*) from `tab{V2_DASHBOARD}` d
        where exists (
            select 1 from `tab{V2_DASHBOARD_ITEM}` i
            where i.parent = d.name
              and i.parenttype = %(parenttype)s
              and coalesce(i.item_type, '') not in (%(text)s, %(filter)s)
        )
        and not exists (
            select 1 from `tab{V3_DASHBOARD}` v3
            where v3.old_name = d.name
        )
        """,
        {"parenttype": V2_DASHBOARD, "text": TEXT_ITEM, "filter": FILTER_ITEM},
    )[0][0]


@insights_whitelist()
def get_v2_migration_nudge() -> dict:
    """Whether to offer the v2 migration, and the number to say in the offer.

    The banner in v2 and the banner in v3 ask this one question, so the rule
    lives here rather than twice in two frontends.

    Three facts settle it, and none of them is "does this site hold v2 rows".
    Nothing deletes those - not an upgrade, not the migrator - so their
    presence can never turn the nudge off:

    - **Something is left to move.** `_v2_dashboards_waiting`.
    - **v2 was used recently.** A team that moved to v3 by hand keeps every v2
      row and stops running them the same day. Use separates them from a team
      still on v2. A row count cannot.
    - **Nobody hid it.** Where the first two cannot decide - a team that
      upgraded last month and rebuilt by hand still reads as active - one admin
      answers once, for the whole site.

    Readable by any Insights user, because the v2 banner is shown to whoever
    opens v2, and a count of dashboards they can already see is not a secret.
    `can_migrate` says whether this user is the one who can act on it.
    """
    hidden = bool(frappe.db.get_global(NUDGE_HIDDEN_KEY))
    waiting = 0 if hidden else _v2_dashboards_waiting()
    last_used = _v2_last_used() if waiting else None
    cutoff = add_days(now_datetime(), -V2_ACTIVE_WITHIN_DAYS)
    nudge = {
        "show": bool(last_used) and get_datetime(last_used) > cutoff,
        "waiting": waiting,
        "can_migrate": _can_migrate(),
        # A hidden nudge counts nothing waiting, so `waiting` alone cannot tell
        # "the site is done" from "somebody switched this off". The page that
        # offers to switch it back on has to know which.
        "hidden": hidden,
    }

    # The top of the funnel: this user was offered the migration today. Which
    # surface offered it is not said here - one call answers both frontends, and
    # the rate limit keys on the event and the user, so a property could not
    # separate them. `v2_migration_page_opened` carries the entry point instead.
    if nudge["show"]:
        _capture(
            "v2_migration_offered",
            {"waiting": waiting, "can_migrate": nudge["can_migrate"]},
            interval="1d",
        )
    return nudge


def _can_migrate() -> bool:
    """The same test `migrate_v2_dashboards` applies.

    Asked through `has_role`, which is what `insights_whitelist` enforces. A
    second copy of the rule here would drift, and the UI would then offer a
    button the endpoint refuses.
    """
    return has_role(MIGRATION_ROLE)


@insights_whitelist(role=MIGRATION_ROLE)
def set_v2_migration_nudge(hidden: bool) -> None:
    """Stop offering the migration, or start offering it again.

    A global default and not a browser key. Whoever decides the site is done
    with v2 decides it for the site: a browser key would ask them again on
    their next machine, and would leave every other admin still being asked.

    One endpoint that takes the state, and not a `hide` beside a `show`. The two
    are one decision, and the site-wide reach is what makes the way back
    necessary - an admin who hides this for everyone from a one-click banner
    must be able to undo it from the page that owns the migration.
    """
    if hidden:
        # Counted before the write, because after it `_v2_dashboards_waiting`
        # reads zero. How much a site walks away from is the point of the event.
        _capture("v2_migration_dismissed", {"waiting": _v2_dashboards_waiting()})
        frappe.db.set_global(NUDGE_HIDDEN_KEY, "1")
        return

    frappe.db.set_global(NUDGE_HIDDEN_KEY, None)
    # How often the way back is used says whether hiding it was too easy.
    _capture("v2_migration_restored", {"waiting": _v2_dashboards_waiting()})


@insights_whitelist(role=MIGRATION_ROLE)
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

    _capture(
        "v2_migration_started",
        {
            "accepted": len(accepted),
            "skipped": len(skipped),
            "reasons": sorted({entry["reason"] for entry in skipped}),
        },
    )
    return {"accepted": accepted, "skipped": skipped}


@insights_whitelist(role=MIGRATION_ROLE)
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

    for name, state in status.items():
        state["verification"] = _verification_summary(read_verification(name))
    return status


@insights_whitelist(role=MIGRATION_ROLE)
def get_v2_verification(dashboard: str) -> dict | None:
    """What the numbers check found, query by query. Nothing until one has run."""
    _require_v2_dashboard(dashboard)
    return read_verification(dashboard)


# -- verifying --------------------------------------------------------------

VERIFICATION_KEY = "insights_v2_verification"


def verification_key(dashboard: str) -> str:
    return f"{VERIFICATION_KEY}:{dashboard}"


def read_verification(dashboard: str) -> dict | None:
    stored = frappe.db.get_global(verification_key(dashboard))
    if not stored:
        return None
    try:
        return json.loads(stored)
    except ValueError:
        return None


def _verification_summary(stored: dict | None) -> dict | None:
    """The one line the page shows: how many charts were checked, and which
    of them disagree with v2."""
    if not stored:
        return None
    return {
        "checked": stored.get("checked", 0),
        "same": stored.get("same", 0),
        "expected": stored.get("expected", 0),
        "different": stored.get("different", 0),
        "not_checked": stored.get("not_checked", 0),
        "differing_charts": stored.get("differing_charts", []),
    }


def store_verification(result, report) -> dict:
    """Keep one migration's verification where the page can read it later.

    A global default rather than a doctype, for the reason the module docstring
    gives. The stored shape is already per chart, because "which chart shows
    different numbers" is the only question anybody asks of it - the v3 query
    docname is kept beside each one for whoever has to chase it.
    """
    charts_by_query: dict[str, list[str]] = {}
    for chart in result.plan.dashboard.charts if result.plan.dashboard else []:
        if chart.query:
            charts_by_query.setdefault(chart.query, []).append(chart.title or chart.source)

    queries = []
    for check in report.verifications:
        queries.append(
            {
                "query": check.source,
                "target": check.target,
                "charts": charts_by_query.get(check.source, []),
                "verdict": check.verdict,
                "reason": check.reason,
                "differences": [
                    {"kind": difference.kind, "detail": difference.detail, "column": difference.column}
                    for difference in check.unexpected
                ],
            }
        )

    differing = [title for entry in queries if entry["verdict"] == DIFFERENT for title in entry["charts"]]
    stored = {
        "dashboard": result.plan.source,
        "workbook": result.workbook,
        "checked_at": frappe.utils.now(),
        "checked": len(queries),
        "same": len([entry for entry in queries if entry["verdict"] == SAME]),
        # A difference a gap already predicted is not news: the user read that
        # gap before migrating, so it counts as agreement, not as a surprise.
        "expected": len([entry for entry in queries if entry["verdict"] == EXPECTED]),
        "different": len([entry for entry in queries if entry["verdict"] == DIFFERENT]),
        "not_checked": len(
            [entry for entry in queries if entry["verdict"] not in (SAME, EXPECTED, DIFFERENT)]
        ),
        "differing_charts": sorted(set(differing)),
        "queries": queries,
        "report": report.report,
    }
    frappe.db.set_global(verification_key(result.plan.source), json.dumps(stored))
    return stored


# -- the job ----------------------------------------------------------------


def run_v2_dashboard_migration(dashboard: str) -> dict:
    """Migrate one v2 dashboard. The worker's entry point.

    Not whitelisted: it is reached through the queue, and `migrate_v2_dashboards`
    is the only thing that puts it there. It re-checks the dashboard exists
    because a job outlives the request that queued it.
    """
    if not _existing_v2_dashboards([dashboard]):
        frappe.throw(frappe._("Dashboard {0} not found").format(dashboard))

    try:
        result = migrate_dashboard(dashboard)
    except Exception as exception:
        # The class name alone. An exception message names the table, column or
        # SQL that broke, and that is the user's data.
        _capture("v2_migration_failed", {"error": type(exception).__name__})
        raise

    # The scan says which group a dashboard belongs in, and this run just moved
    # one of them.
    frappe.cache().delete_value(SCAN_CACHE_KEY)

    verification = _verify(result)
    _capture_outcome(result, verification)

    return {
        "dashboard": result.dashboard,
        "workbook": result.workbook,
        "skipped": result.skipped,
        "report": result.report,
        "verification": verification,
    }


def _capture_outcome(result, verification: dict | None) -> None:
    """What this migration actually produced, and whether the numbers agreed.

    The one event that says the migrator works. It reports the gap kinds the
    plan hit rather than the gaps, so a fleet report answers "which construct
    does the migrator still not carry" without carrying anybody's query.
    """
    if result.skipped:
        return

    plan = result.plan
    summary = verification or {}
    _capture(
        "v2_migration_finished",
        {
            "queries": len(plan.queries),
            "query_kinds": plan.kinds,
            "dropped_queries": len(plan.dropped_queries),
            "items": plan.item_count,
            "items_converted": plan.converted_items,
            "items_dropped": plan.dropped_items,
            "converts_cleanly": plan.converts_cleanly,
            "gap_kinds": _gap_kinds(plan),
            # A verification that did not run is not a verification that agreed,
            # so `verified` says which of the two this is.
            "verified": bool(verification),
            "checked": summary.get("checked", 0),
            "same": summary.get("same", 0),
            "expected": summary.get("expected", 0),
            "different": summary.get("different", 0),
            "not_checked": summary.get("not_checked", 0),
        },
    )


def _verify(result) -> dict | None:
    """Check the migrated queries against v2's own answers, and keep the result.

    Inside the job because it runs both sides of every query, and after the
    write because it has nothing to compare until then. A verification that
    fails is not a migration that failed: the workbook is written and correct
    as far as anything here knows, so the failure is logged and the migration
    stands.
    """
    if result.skipped or not result.workbook:
        return None
    try:
        return store_verification(result, verify_migration(result))
    except Exception:
        frappe.log_error(f"v2 migration verification failed for {result.plan.source}")
        return None


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
