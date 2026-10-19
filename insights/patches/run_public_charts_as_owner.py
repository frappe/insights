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
        if publisher == owner or not why_rows_differ(chart, publisher, owner):
            frappe.db.set_value(CHART, chart, "run_as_owner", 1, update_modified=False)
        elif frappe.db.get_value("User", publisher, "enabled"):
            frappe.db.set_value(CHART, chart, {"owner": publisher, "run_as_owner": 1}, update_modified=False)
            report(chart, owner, publisher, moved=True)
        else:
            report(chart, owner, publisher, moved=False)


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


def why_rows_differ(chart: str, publisher: str, owner: str) -> str | None:
    """Why `chart` may show other rows to its owner than to its publisher, or
    None when it shows both the same rows.

    Desk permissions filter site data, and a team's Table Restrictions filter
    external data, both per user. A script, or an expression that calls frappe,
    can read anything the running user can. A chart that uses none of these, on
    tables both users may read, shows both the same rows.
    """
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import is_site_db
    from insights.insights.doctype.insights_team.insights_team import check_table_permission, team_grant
    from insights.insights.query_utils import source_tables, transitive_closure

    query, config = frappe.db.get_value(CHART, chart, ["query", "config"])
    if not query:
        return "has no query"

    queries = {query, *transitive_closure(query)}
    operations = frappe.get_all(
        "Insights Query v3", filters={"name": ("in", list(queries))}, pluck="operations"
    )
    if any(runs_as_user(frappe.parse_json(content)) for content in [config, *operations]):
        return "runs a script or an expression that calls frappe"

    for table in source_tables(query):
        data_source, table_name = table["data_source"], table["table_name"]
        if is_site_db(data_source):
            return f"reads the site table {table_name}"
        for user in (publisher, owner):
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
