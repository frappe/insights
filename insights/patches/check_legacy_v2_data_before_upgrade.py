import frappe


def execute():
    if not frappe.db.count("Insights Query"):
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
⚠️  Insights v2 is being discontinued — Upgrade Blocked

Insights v2 has been permanently removed in this release. Insights v3 is already available with a better experience and ongoing improvements. New features and bug fixes for v2 have already stopped.

Your site has {log_count} query executions in the last 30 days, which means you have active usage. To prevent data loss, the upgrade to v3 has been blocked until you take action.

You can check the migration guide here: https://docs.frappe.io/insights/articles/migrate-from-v2-to-v3

For any questions or help with the migration, please join telegram group: https://t.me/frappeinsights or reach out to support: https://frappe.io/support

If you have already migrated or do not have any active usage, please set the following site config to allow the upgrade:

{{
    "insights_allow_legacy_v2_upgrade": 1
}}

"""

    print(message)
    exit(1)
