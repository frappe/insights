import json
import sys
from collections import defaultdict

import frappe

V2_QUERY = "Insights Query"
V2_DASHBOARD = "Insights Dashboard"
V2_DASHBOARD_ITEM = "Insights Dashboard Item"
USED_WITHIN_DAYS = 30


def execute():
    if not frappe.db.count(V2_QUERY):
        return

    if frappe.conf.get("insights_allow_legacy_v2_upgrade"):
        return

    dashboards, queries = unmigrated_v2_work()
    if not dashboards and not queries:
        return

    message = f"""
⚠️  Insights v2 has been removed — update blocked

Insights 3.50 no longer contains v2 or the v2 migrator. New features and bug fixes for v2 have already stopped.

Your site used v2 in the last 30 days, and some of what it used is not migrated yet. v2 dashboards: {len(dashboards)}. v2 queries outside any dashboard: {len(queries)}. To prevent data loss, the update to Insights 3.50 has been blocked until you take action.

Stay on your current Insights 3 release and migrate your v2 queries and dashboards first. Then update to 3.50.

- On Insights 3.13 or later: as an admin, open Insights, then Settings > Migrate from v2.
- On an older release: update to 3.15.1 first. Self-hosted, check out the `v3.15.1` tag. On Frappe Cloud, contact support.
- The migrator moves dashboards only. For a query outside any dashboard, add it to a v2 dashboard and migrate that dashboard, or rebuild it in v3 and set the site config below.

Once everything used in v2 is migrated, update again. This check passes then.

Migration guide: https://docs.frappe.io/insights/articles/migrate-from-v2-to-v3

For any questions or help with the migration, please join telegram group: https://t.me/frappeinsights or reach out to support: https://frappe.io/support

If you don't need your v2 work, set the site config below. It skips this check, and v2 data you have not migrated is not carried over:

{{
    "insights_allow_legacy_v2_upgrade": 1
}}

"""

    print(message)
    # SystemExit escapes patch_handler's `except Exception`, so `--skip-failing`
    # can't silently bypass the block
    sys.exit(1)


def unmigrated_v2_work() -> tuple[list[str], list[str]]:
    """The v2 dashboards and the v2 queries outside any dashboard that were used
    recently and are not migrated.

    A v2 query is used when it ran: v2 logs each run with its data source, and
    v3 logs none. A dashboard is migrated once an Insights Dashboard v3 holds its
    name in `old_name`, as v3.15.1's migrator records it. That migrator moves
    only dashboards, so a query outside every dashboard counts until a v3 query
    holds its name.

    Plain SQL, because the v2 doctypes are gone from 3.50 and only their tables
    remain.
    """
    cutoff = frappe.utils.add_to_date(frappe.utils.now(), days=-USED_WITHIN_DAYS)
    used = frappe.get_all(
        "Insights Query Execution Log",
        filters={"creation": [">=", cutoff], "data_source": ["is", "set"], "query": ["is", "set"]},
        pluck="query",
        distinct=True,
    )
    used = (
        {
            row[0]
            for row in frappe.db.sql(
                "select name from `tabInsights Query` where name in %(names)s",
                {"names": tuple(used)},
            )
        }
        if used
        else set()
    )
    if not used:
        return [], []

    read_by = defaultdict(set)
    if frappe.db.table_exists(V2_DASHBOARD_ITEM):
        # `select *`: the item's query moved from a column into `options` at
        # different times on different sites
        for item in frappe.db.sql(
            "select * from `tabInsights Dashboard Item` where parenttype = %s",
            V2_DASHBOARD,
            as_dict=True,
        ):
            if query := item.get("query") or item_options(item).get("query"):
                read_by[query].add(item.parent)

    reading = {dashboard for query in used for dashboard in read_by[query]}
    migrated = (
        set(
            frappe.get_all(
                "Insights Dashboard v3", filters={"old_name": ["in", list(reading)]}, pluck="old_name"
            )
        )
        if reading
        else set()
    )
    alone = {query for query in used if not read_by[query]}
    copied = (
        set(frappe.get_all("Insights Query v3", filters={"old_name": ["in", list(alone)]}, pluck="old_name"))
        if alone
        else set()
    )
    return sorted(reading - migrated), sorted(alone - copied)


def item_options(item) -> dict:
    try:
        options = json.loads(item.get("options") or "{}")
    except ValueError:
        return {}  # nosemgrep - an item with unreadable options names no query
    return options if isinstance(options, dict) else {}
