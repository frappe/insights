import frappe

CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"

# The column the base wrote when content was published. It names the person a
# public read filtered its rows by, and `retire_content_permission_user` drops
# it, so this is the last patch that can read it.
PUBLISHER = "permission_user"


def execute():
    """
    Public content runs with its owner's permissions, so content already
    published running as its reader drew an empty page for the
    guests it was published for.

    A chart reaches a guest two ways - on its own level, or through a Public
    dashboard it is linked to - and both are named here, because the update that
    names them from now on runs on the dashboard's save.

    Checked only where the owner's rows are the rows the base was already
    serving. The base filtered a public read by the user the *publishing*
    document recorded, and that is the chart's own owner for most content and
    somebody else for a chart another person's dashboard published. Where they
    differ, neither answer is writable any more: the column is going, and
    `validate_run_as_owner` lets nobody but the owner hand out the owner's rows.
    So the box stays unchecked there, unless the two read the same rows, and the
    card refuses rather than serving a third person's rows to the open internet.
    Its owner can check it from the chart's share dialog, which is the one place
    that decision belongs.
    """
    left = []
    for chart, publisher in publicly_reachable_charts().items():
        if not publisher:
            continue
        owner = frappe.db.get_value(CHART, chart, "owner")
        reason = None if publisher == owner else why_rows_differ(chart, publisher, owner)
        if reason:
            left.append((chart, owner, publisher, reason))
        else:
            frappe.db.set_value(CHART, chart, "run_as_owner", 1, update_modified=False)

    if not left:
        return
    print(
        f"Insights: {len(left)} public chart(s) left running as their reader; "
        "their owner can turn on Run as owner in the chart's share dialog"
    )
    for chart, owner, publisher, reason in left:
        title = frappe.db.get_value(CHART, chart, "title")
        print(f'  {chart} "{title}": owner {owner}, published by {publisher}: {reason}')


def why_rows_differ(chart: str, publisher: str, owner: str) -> str | None:
    """Why `chart` may draw other rows for its owner than for its publisher, or
    nothing where it draws the same rows for both.

    Site data is filtered by desk's permissions and external data by a team's
    Table Restrictions, both per user. A script, or an expression that calls
    frappe, can read anything the running user can. A chart that uses none of
    them, on tables both may read, draws the same rows for both.
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

    The base read that user off the document that published the chart: the chart
    itself when it was published in its own right, else the oldest Public
    dashboard holding it. Same precedence here, so the answer is the one the
    link was serving.
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
    """The user this document's publisher recorded.

    A site on a release before the column came never had it, and its published
    content is served as the publishing document's owner - what the base's own
    backfill writes into the column when it adds it.
    """
    if not frappe.db.has_column(doctype, PUBLISHER):
        return frappe.db.get_value(doctype, name, "owner")

    return frappe.db.get_value(doctype, name, PUBLISHER)
