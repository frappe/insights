import frappe

from insights.upgrade import add_item

CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"

# The column the base wrote when content was published. It names the user whose
# permissions filtered a public read. `retire_content_permission_user` drops it,
# so this is the last patch that can read it.
PUBLISHER = "permission_user"


def execute():
    """
    Public content runs with its owner's permissions. Content published
    earlier runs as its reader, so it showed an empty page to the guests it was
    published for.

    A guest reaches a chart two ways: at the chart's own visibility level, or
    through a Public dashboard that shows it. This patch handles both. From now
    on, the dashboard's save handles the second.

    The base filtered a public read by the user the *publishing* document
    recorded. For most content that is the chart's own owner, and Run as owner
    is checked. For a chart that another person's dashboard published, it is
    someone else, and the column that named them is going. Where the owner
    reads other rows than the publisher, the publisher becomes the owner, so
    the link keeps serving the rows it served. The publisher chose to publish
    those rows, and `validate_run_as_owner` lets only the owner share them.
    The previous owner is told. A disabled publisher can run nothing, so that
    chart is left running as its reader, and its owner is told.
    """
    for chart, publisher in publicly_reachable_charts().items():
        if not publisher:
            continue
        owner = frappe.db.get_value(CHART, chart, "owner")
        if not owner:
            continue  # a dashboard row naming a chart that was deleted
        if publisher == owner or not why_rows_differ(chart, publisher, owner):
            frappe.db.set_value(CHART, chart, "run_as_owner", 1, update_modified=False)
            report_reader_rows(chart, owner)
        elif frappe.db.get_value("User", publisher, "enabled"):
            frappe.db.set_value(CHART, chart, {"owner": publisher, "run_as_owner": 1}, update_modified=False)
            keep_edit(chart, owner)
            report(chart, owner, publisher, moved=True)
        else:
            report(chart, owner, publisher, moved=False)


def keep_edit(chart: str, previous_owner: str) -> None:
    """Share the chart's workbook with its previous owner to edit.

    The workbook share patch runs later and shares a workbook with the owners
    of its members. The chart no longer names its previous owner, so it would
    leave them out.
    """
    from insights.patches.share_workbooks_with_member_owners import WORKBOOK, share_workbook
    from insights.permissions import get_insights_users

    workbook = frappe.db.get_value(CHART, chart, "workbook")
    if (
        workbook
        and previous_owner in get_insights_users()
        and not frappe.has_permission(WORKBOOK, "write", doc=workbook, user=previous_owner)
    ):
        share_workbook(workbook, previous_owner, write=1)


def report(chart: str, owner: str, publisher: str, moved: bool) -> None:
    title = frappe.db.get_value(CHART, chart, "title") or chart
    if moved:
        message = (
            f'Public chart "{title}" now belongs to {publisher}, who published it, and runs as its owner. '
            f"Its public link keeps showing the rows {publisher} can see, as before. It belonged to {owner}."
        )
    else:
        message = (
            f'Public chart "{title}" was published by {publisher}, whose account is disabled, so it now runs '
            f"as each reader and guests see nothing. To show {owner}'s rows to guests, turn on Run as owner "
            "in its share dialog."
        )
    add_item("P11", message, reference=(CHART, chart), user=None if owner == "Administrator" else owner)


def report_reader_rows(chart: str, owner: str) -> None:
    """A signed-in reader saw their own rows of a public chart in Insights 3.
    Run as owner shows every reader the owner's rows."""
    query, config, title = frappe.db.get_value(CHART, chart, ["query", "config", "title"])
    why = why_rows_follow_reader(query, config)
    if not why:
        return
    add_item(
        "P10",
        f'Public chart "{title or chart}" now runs as its owner, {owner}, so every signed-in reader sees '
        f"{owner}'s rows instead of their own, because {why}. To show each reader their own rows, stop "
        "sharing the chart and its dashboards publicly, then turn off Run as owner.",
        reference=(CHART, chart),
        user=None if owner == "Administrator" else owner,
    )


def why_rows_follow_reader(query: str | None, content) -> str | None:
    """Why `query`, and `content` that reads its rows, may give each reader
    other rows, or None when every reader gets the same rows."""
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name, is_site_db
    from insights.insights.query_utils import source_tables, transitive_closure

    if not query:
        return None
    operations = frappe.get_all(
        "Insights Query v3", filters={"name": ("in", [query, *transitive_closure(query)])}, pluck="operations"
    )
    if any(runs_as_user(frappe.parse_json(node)) for node in [content, *operations]):
        return "it runs a script or an expression that calls frappe"

    restrictions_apply = frappe.db.get_single_value("Insights Settings", "enable_permissions")
    for table in source_tables(query):
        data_source, table_name = table["data_source"], table["table_name"]
        if is_site_db(data_source):
            return f"it reads {table_name.removeprefix('tab')}, which desk permissions filter"
        if restrictions_apply and frappe.db.exists(
            "Insights Resource Permission",
            {
                "resource_type": "Insights Table v3",
                "resource_name": get_table_name(data_source, table_name),
                "table_restrictions": ("is", "set"),
            },
        ):
            return f"a Table Restriction filters {table_name}"
    return None


def why_rows_differ(chart: str, publisher: str, owner: str) -> str | None:
    """Why `chart` may show other rows to its owner than to its publisher, or
    None when it shows both the same rows."""
    query, config = frappe.db.get_value(CHART, chart, ["query", "config"])
    return why_query_rows_differ(query, config, (publisher, owner))


def why_query_rows_differ(query: str | None, content, users: tuple[str, str]) -> str | None:
    """Why `query`, and `content` that reads its rows (a chart's config, an
    alert's condition), may give the two `users` other rows, or None when it
    gives both the same rows.

    Desk permissions filter site data, and a team's Table Restrictions filter
    external data, both per user. A script, or an expression that calls frappe,
    can read anything the running user can. A query that uses none of these, on
    tables both users may read, gives both the same rows.
    """
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import is_site_db
    from insights.insights.doctype.insights_team.insights_team import check_table_permission, team_grant
    from insights.insights.query_utils import source_tables, transitive_closure

    if not query:
        return "has no query"

    queries = {query, *transitive_closure(query)}
    operations = frappe.get_all(
        "Insights Query v3", filters={"name": ("in", list(queries))}, pluck="operations"
    )
    if any(runs_as_user(frappe.parse_json(node)) for node in [content, *operations]):
        return "runs a script or an expression that calls frappe"

    for table in source_tables(query):
        data_source, table_name = table["data_source"], table["table_name"]
        if is_site_db(data_source):
            return f"reads the site table {table_name}"
        for user in users:
            if not check_table_permission(data_source, table_name, user=user, raise_error=False):
                return f"{user} cannot read {data_source}.{table_name}"
            if team_grant(data_source, table_name, user=user):
                return f"a Table Restriction narrows {data_source}.{table_name} for {user}"
    return None


def runs_as_user(node) -> bool:
    """Whether `node` holds a script, or an expression that calls frappe."""
    if isinstance(node, list):
        return any(runs_as_user(value) for value in node)
    if not isinstance(node, dict):
        return False
    if node.get("type") == "code":
        return True
    expression = node.get("expression")
    if isinstance(expression, str) and "frappe" in expression:
        return True
    return any(runs_as_user(value) for value in node.values())


def publicly_reachable_charts() -> dict[str, str | None]:
    """Every chart a public link reaches, and the user the base ran it as.

    The base read that user from the document that published the chart. That is
    the chart itself when it was published on its own, and otherwise the oldest
    Public dashboard that shows it. This uses the same order, so the answer
    matches what the link served.
    """
    charts = {
        chart: publisher_of(CHART, chart)
        for chart in frappe.get_all(CHART, filters={"visibility": "Public"}, pluck="name")
    }

    for dashboard in frappe.get_all(
        DASHBOARD, filters={"visibility": "Public"}, order_by="creation asc", pluck="name"
    ):
        publisher = publisher_of(DASHBOARD, dashboard)
        for chart in frappe.get_all(
            "Insights Dashboard Chart v3",
            filters={"parenttype": DASHBOARD, "parent": dashboard},
            pluck="chart",
        ):
            charts.setdefault(chart, publisher)

    return charts


def publisher_of(doctype: str, name: str) -> str | None:
    """The user recorded by this document's publisher.

    A site on a release before the column existed never had it. Its published
    content ran as the publishing document's owner, which is what the base's
    own backfill writes when it adds the column.
    """
    if not frappe.db.has_column(doctype, PUBLISHER):
        return frappe.db.get_value(doctype, name, "owner")

    return frappe.db.get_value(doctype, name, PUBLISHER)
