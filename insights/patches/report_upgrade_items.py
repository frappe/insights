"""List what the upgrade from Insights v3 leaves for an admin or an author to do.

Nothing here changes data. Each finding becomes an upgrade item. Runs after
the patches that share workbooks, because those decide who may edit what.
"""

import os

import frappe
from frappe.utils import get_date_str

from insights.upgrade import add_item, standard_workbook_of, template_copies, was_on_v3

WORKBOOK = "Insights Workbook"
QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"
ALERT = "Insights Alert"
IMPORT_JOB = "Insights Table Import Job"
TEAM = "Insights Team"
SETTINGS = "Insights Settings"
# the globals an import job's script runs with besides the sandbox's
IMPORT_JOB_NAMES = ("client", "table", "state", "secrets", "log")
# a template import inserts its documents in one request
IMPORT_SECONDS = 300
# why a chart cannot run as its owner, by reason
OWNER_CANNOT_RUN = {
    "disabled": "is disabled",
    "no_insights_role": "has no Insights role",
    "cannot_edit": "can't edit its workbook",
}


def execute():
    # a develop site has run with each of these since it moved off Insights v3
    if not was_on_v3():
        return
    report_team_grants_that_lost_write()
    report_charts_that_cannot_run_as_owner()
    report_trusted_code_of_authors()
    report_scripts_with_refused_names()
    report_template_copies()
    report_blank_fiscal_year_start()


def report_team_grants_that_lost_write():
    """P4: a team grant on a dashboard or chart let its members edit it in
    Insights v3. It gives read now, and only the workbook gives write."""
    from insights.insights.doctype.insights_team.insights_team import clear_cache, is_admin

    if not frappe.db.get_single_value(SETTINGS, "enable_permissions"):
        return
    clear_cache()
    grants = frappe.get_all(
        "Insights Resource Permission",
        filters={"parenttype": TEAM, "resource_type": ("in", (DASHBOARD, CHART))},
        fields=["parent", "resource_type", "resource_name"],
        order_by="parent asc, idx asc",
    )
    lost: dict[str, frappe._dict] = {}
    for grant in grants:
        item = frappe.db.get_value(
            grant.resource_type, grant.resource_name, ["title", "workbook"], as_dict=True
        )
        if not item or not item.workbook:
            continue
        members = frappe.get_all(
            "Insights Team Member", filters={"parent": grant.parent}, pluck="user", order_by="user asc"
        )
        users = [
            user
            for user in frappe.get_all(
                "User", filters={"name": ("in", members or [""]), "enabled": 1}, pluck="name"
            )
            if not is_admin(user)
            and not frappe.has_permission(WORKBOOK, "write", doc=item.workbook, user=user)
        ]
        if not users:
            continue
        found = lost.setdefault(item.workbook, frappe._dict(teams=set(), titles=set(), users=set()))
        found.teams.add(grant.parent)
        found.titles.add(item.title or grant.resource_name)
        found.users.update(users)

    for workbook, found in lost.items():
        data = {"items": sorted(found.titles), "users": sorted(found.users), "teams": sorted(found.teams)}
        add_item(
            "P4",
            f"{quoted(data['items'])}: {', '.join(data['users'])} edited them through "
            f"{plural('team', data['teams'])} {', '.join(data['teams'])}",
            reference=(WORKBOOK, workbook),
            data=data,
        )


def report_charts_that_cannot_run_as_owner():
    """P12: Insights v3 ran a public chart as its publisher whatever happened to
    them. A chart runs as its owner only while the owner may edit it."""
    from insights.permission_user import may_run_as
    from insights.permissions import get_insights_users

    insights_users = get_insights_users()
    for chart in frappe.get_all(CHART, filters={"run_as_owner": 1}, fields=["name", "title", "owner"]):
        if chart.owner == "Administrator" or may_run_as(CHART, chart.name, chart.owner):
            continue
        if not frappe.db.get_value("User", chart.owner, "enabled"):
            reason = "disabled"
        elif chart.owner not in insights_users:
            reason = "no_insights_role"
        else:
            reason = "cannot_edit"
        data = {"chart": chart.title or chart.name, "owner": chart.owner, "reason": reason}
        add_item(
            "P12",
            f'"{data["chart"]}": its owner, {chart.owner}, {OWNER_CANNOT_RUN[reason]}',
            reference=(CHART, chart.name),
            data=data,
        )


def report_trusted_code_of_authors():
    """P20: only an Insights Admin changes a script, an expression that runs SQL
    or a stored procedure call now. What is stored keeps running."""
    from insights.insights.doctype.insights_team.insights_team import is_admin
    from insights.permissions import trusted_code_of

    for doctype, field in ((QUERY, "operations"), (CHART, "config"), (ALERT, "condition")):
        for doc in frappe.get_all(doctype, fields=["name", "title", "owner", field]):
            content = {"expression": doc[field]} if doctype == ALERT else doc[field]
            if doc.owner == "Administrator" or is_admin(doc.owner) or not trusted_code_of(content):
                continue
            data = {"title": doc.title or doc.name, "author": doc.owner}
            add_item(
                "P20",
                f'"{data["title"]}" by {doc.owner}',
                reference=(doctype, doc.name),
                user=doc.owner,
                data=data,
            )


def report_scripts_with_refused_names():
    """Q1 and J4: a script runs with a short list of names now, and a name off
    the list fails the run. A failing import job stops syncing its table."""
    from insights.insights.doctype.insights_data_source_v3.sandbox import refused_names

    for query in frappe.get_all(
        QUERY, filters={"is_script_query": 1}, fields=["name", "title", "owner", "operations"]
    ):
        operations = frappe.parse_json(query.operations) or []
        code = "\n".join(
            op.get("code") or "" for op in operations if isinstance(op, dict) and op.get("type") == "code"
        )
        if names := refused_names(code):
            data = {"title": query.title or query.name, "names": names}
            add_item(
                "Q1",
                uses_message(data),
                reference=(QUERY, query.name),
                user=author(query.owner),
                data=data,
            )

    for job in frappe.get_all(IMPORT_JOB, fields=["name", "title", "owner", "script", "enabled"]):
        if names := refused_names(job.script or "", IMPORT_JOB_NAMES):
            data = {"title": job.title or job.name, "names": names}
            add_item(
                "J4",
                uses_message(data),
                reference=(IMPORT_JOB, job.name),
                user=author(job.owner),
                data=data,
            )


def uses_message(data: dict) -> str:
    return f'"{data["title"]}" uses {", ".join(f"`{name}`" for name in data["names"])}'


def report_template_copies():
    """W2: a workbook made from an Insights v3 template. An app now ships the
    standard workbook that replaces it, and the copy gets no more updates."""
    from insights import standard

    for copy in template_copies():
        standard_name = standard_workbook_of(copy.from_template)
        shipped = standard_name and shipped_by(standard, standard_name)
        if not shipped:
            continue
        # Insights v3 counted a copy without a checksum as changed
        untouched = bool(copy.get("imported_checksum")) and is_untouched(copy.name)
        data = {"workbook": copy.title, **shipped, "untouched": untouched}
        add_item(
            "W2",
            f'"{copy.title}": replaced by "{data["standard"]}", '
            + ("never changed" if untouched else "may have been changed"),
            reference=(WORKBOOK, copy.name),
            action="delete_workbook" if untouched else None,
            data=data,
        )


def shipped_by(standard, name: str) -> dict | None:
    """The title of the standard workbook `name` as `standard`, and of the
    installed app that ships it as `app`. Read from the file: a migrate imports
    it after the patches."""
    for app, module in standard.app_modules():
        path = standard.file_path(WORKBOOK, name, module)
        if os.path.exists(path):
            app_title = frappe.get_hooks("app_title", app_name=app)
            return {
                "standard": frappe.get_file_json(path).get("title") or name,
                "app": app_title[0] if app_title else app,
            }
    return None


def is_untouched(workbook: str) -> bool:
    """Whether every query, chart and dashboard of `workbook` is as the template
    import made it: made in one go, and not changed since.

    Insights v3's own checksum read its export, which the patches have changed.
    A patch that saved a document makes it look changed, which only means no
    delete is offered.
    """
    times = [
        (row.creation, row.modified)
        for doctype in (QUERY, CHART, DASHBOARD)
        for row in frappe.get_all(doctype, filters={"workbook": workbook}, fields=["creation", "modified"])
    ]
    if not times:
        return False
    first = min(creation for creation, _ in times)
    return all((modified - first).total_seconds() <= IMPORT_SECONDS for _, modified in times)


def report_blank_fiscal_year_start():
    """Q13: a blank Fiscal Year Start follows ERPNext's current fiscal year.
    Insights v3 started the year on 1 April for date filters and 1 January for
    fiscal-year groups."""
    from insights.insights.query_builders.sql_functions import get_fiscal_year_start_date

    stored = frappe.db.get_single_value(SETTINGS, "fiscal_year_start")
    if stored and get_date_str(stored) != "0001-01-01":
        return
    start = get_fiscal_year_start_date()
    add_item(
        "Q13",
        f"Fiscal years now start on {start.day} {start.strftime('%B')}",
        action="open_settings",
        data={"start": start.isoformat()},
    )


def author(owner: str) -> str | None:
    """The user an item concerns. Administrator is an admin, who sees every item."""
    return None if owner == "Administrator" else owner


def plural(word: str, items) -> str:
    return word if len(items) == 1 else f"{word}s"


def quoted(titles) -> str:
    return ", ".join(f'"{title}"' for title in sorted(titles))
