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

    Checked only where the owner is who the base was already serving. The base
    filtered a public read by the user the *publishing* document recorded, and
    that is the chart's own owner for most content and somebody else for a chart
    another person's dashboard published. Where they differ, neither answer is
    writable any more: the column is going, and `validate_run_as_owner` lets
    nobody but the owner hand out the owner's rows. So the box stays unchecked
    there and the card refuses, rather than serving a third person's rows to the
    open internet. Its owner can check it from the chart's share dialog, which
    is the one place that decision belongs.
    """
    for chart, publisher in publicly_reachable_charts().items():
        if publisher and publisher == frappe.db.get_value(CHART, chart, "owner"):
            frappe.db.set_value(CHART, chart, "run_as_owner", 1, update_modified=False)


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
