import sys

import frappe


def execute():
    if not frappe.db.count("Insights Query"):
        return

    if frappe.conf.get("insights_allow_legacy_v2_upgrade"):
        return

    log_count = frappe.db.count(
        "Insights Query Execution Log",
        filters={
            "creation": [">=", frappe.utils.add_to_date(frappe.utils.now(), days=-30)],
            "data_source": ["is", "set"],
            "query": ["is", "set"],
        },
    )

    if not log_count:
        return

    message = f"""
⚠️  Insights v2 has been removed — update blocked

Insights 3.50 no longer contains v2 or the v2 migrator. New features and bug fixes for v2 have already stopped.

Your site has {log_count} query executions in the last 30 days, which means you have active usage. To prevent data loss, the update to Insights 3.50 has been blocked until you take action.

Stay on your current Insights 3 release and migrate your v2 queries and dashboards first. Then update to 3.50.

- On Insights 3.13 or later: as an admin, open Insights, then Settings > Migrate from v2.
- On an older release: update to 3.15.1 first. Self-hosted, check out the `v3.15.1` tag. On Frappe Cloud, contact support.

Migration guide: https://docs.frappe.io/insights/articles/migrate-from-v2-to-v3

For any questions or help with the migration, please join telegram group: https://t.me/frappeinsights or reach out to support: https://frappe.io/support

If you have already migrated, or you don't need your v2 work, set the site config below. It skips this check, and v2 data you have not migrated is not carried over:

{{
    "insights_allow_legacy_v2_upgrade": 1
}}

"""

    print(message)
    # SystemExit escapes patch_handler's `except Exception`, so `--skip-failing`
    # can't silently bypass the block
    sys.exit(1)
