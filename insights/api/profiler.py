# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The profiler, for an Insights Admin with no shell on the host.

Record a window of real use, then read what happened in it. Or queue a profile
of a dashboard, charts, queries or recorded statements, and read its report
when the job finishes. See `insights.profiler`.
"""

import time

import frappe

from insights.decorators import insights_whitelist
from insights.profiler import events, job, report


@insights_whitelist(role="Insights Admin", methods=["POST"])
def start_recording(minutes: int = 60):
    """Record every Insights request, query, warehouse open and job for `minutes` (at most a day)."""
    return {"recording_until": events.start_recording(minutes)}


@insights_whitelist(role="Insights Admin", methods=["POST"])
def stop_recording():
    events.stop_recording()
    return {"recording_until": None}


@insights_whitelist(role="Insights Admin", methods=["POST"])
def recording_status():
    return {"recording_until": events.recording_until(), "files": events.files()}


@insights_whitelist(role="Insights Admin", methods=["POST"])
def recording_report(
    minutes: int = 60,
    since: float | None = None,
    until: float | None = None,
    dashboard: str | None = None,
    chart: str | None = None,
):
    """What the recorder saw: the last `minutes`, or `since`..`until` as epoch seconds."""
    until = float(until or time.time())
    since = float(since or until - max(1, int(minutes)) * 60)
    if until - since > 7 * 24 * 3600:
        frappe.throw(frappe._("Ask for at most seven days at a time"))
    return report.summarize(since, until, dashboard=dashboard, chart=chart)


@insights_whitelist(role="Insights Admin", methods=["POST"])
def start_profile(
    dashboard: str | None = None,
    charts: list | None = None,
    queries: list | None = None,
    statements: list | None = None,
    slowest: int | None = None,
    options: dict | None = None,
):
    """Queue a profile of one target, and answer its id.

    Name exactly one of: a dashboard; charts; queries, as the execution log
    names them; statements the recorder kept, by digest; or how many of the
    slowest data store queries of the past week. `options` overrides
    `insights.profiler.job.DEFAULTS`.
    """
    target = {
        "dashboard": dashboard,
        "charts": charts,
        "queries": queries,
        "statements": statements,
        "slowest": slowest,
    }
    named = {k: v for k, v in target.items() if v}
    if len(named) != 1:
        frappe.throw(frappe._("Name exactly one target: dashboard, charts, queries, statements or slowest"))
    if dashboard and not frappe.db.exists("Insights Dashboard v3", dashboard):
        frappe.throw(frappe._("No dashboard {0}").format(dashboard), frappe.DoesNotExistError)
    return {"profile": job.start(named, _checked(options or {}))}


def _checked(options: dict) -> dict:
    """Keep the options a caller may set, within bounds."""
    unknown = set(options) - set(job.DEFAULTS)
    if unknown:
        frappe.throw(frappe._("Unknown options: {0}").format(", ".join(sorted(unknown))))
    if "max_seconds" in options:
        options["max_seconds"] = max(5, min(int(options["max_seconds"]), 1800))
    if "experiment_statements" in options:
        options["experiment_statements"] = max(0, min(int(options["experiment_statements"]), 10))
    if "copies" in options:
        options["copies"] = sorted({max(1, min(int(n), 16)) for n in options["copies"]})
    return options


@insights_whitelist(role="Insights Admin", methods=["POST"])
def get_profile(profile: str):
    """A profile's progress, and its report once it has one."""
    found = job.status(profile)
    if not found:
        frappe.throw(frappe._("No profile {0}").format(profile), frappe.DoesNotExistError)
    return {"status": found, "report": job.report(profile)}


@insights_whitelist(role="Insights Admin", methods=["POST"])
def list_profiles(limit: int = 20):
    return job.recent(max(1, min(int(limit), 100)))


@insights_whitelist(role="Insights Admin", methods=["POST"])
def get_statement(digest: str):
    """The SQL text kept under a digest, by a profile or by the recorder."""
    sql = events.read_sql(digest)
    if sql is None:
        frappe.throw(frappe._("No statement {0}").format(digest), frappe.DoesNotExistError)
    return {"digest": digest, "sql": sql}
