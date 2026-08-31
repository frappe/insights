import frappe
from frappe.query_builder import DocType

public_doctypes = [
    "Insights Dashboard v3",
    "Insights Chart v3",
    "Insights Query v3",
]


def check_public_access(doctype, name):
    if not is_public(doctype, name):
        raise frappe.PermissionError("You don't have permission to access this document")


def is_public(doctype: str, name: str):
    # run_doc_method reads `name` out of a parsed JSON blob, which frappe checks
    # only as a whole, so a dict can arrive here and reach frappe.db as a
    # filter set. Nothing but a name names a public document.
    if not isinstance(name, str):
        return False
    if doctype not in public_doctypes:
        return False
    if is_being_previewed(doctype, name):
        return True

    return get_public_root(doctype, name) is not None


def get_public_root(doctype: str, name: str) -> tuple[str, str] | None:
    """The published document that makes `doctype`/`name` reachable without a login.

    A query is reachable because a chart is published, and a chart because it or
    a dashboard holding it is. Publishing is where the permission user is
    recorded, so the root is what names the user a public execution runs as.

    Content can sit under more than one root - a query behind two public charts,
    a chart on two public dashboards. Each of those publishers granted it, so any
    of them is a correct answer. Take the oldest, so it is the same answer every
    time: an unordered `LIMIT 1` moves between MariaDB and Postgres, and the
    identity decides the rows.
    """
    if doctype == "Insights Dashboard v3":
        return ("Insights Dashboard v3", name) if is_public_dashboard(name) else None

    if doctype == "Insights Chart v3":
        return get_chart_root(name)

    if doctype == "Insights Query v3":
        for chart in get_charts_built_on(name):
            root = get_chart_root(chart)
            if root:
                return root

    return None


def get_chart_root(name: str) -> tuple[str, str] | None:
    """A chart is published in its own right, or by a dashboard that holds it."""
    if frappe.db.get_value("Insights Chart v3", name, "is_public"):
        return ("Insights Chart v3", name)

    dashboard = get_public_dashboard_holding(name)
    return ("Insights Dashboard v3", dashboard) if dashboard else None


def get_public_dashboard_holding(chart: str) -> str | None:
    """The oldest published dashboard `chart` sits on."""
    Dashboard = DocType("Insights Dashboard v3")
    DashboardChart = DocType("Insights Dashboard Chart v3")

    holders = (
        frappe.qb.from_(DashboardChart).select(DashboardChart.parent).where(DashboardChart.chart == chart)
    )
    public = (
        frappe.qb.from_(Dashboard)
        .select(Dashboard.name)
        .where((Dashboard.is_public == 1) & Dashboard.name.isin(holders))
        .orderby(Dashboard.creation)
        .limit(1)
        .run(pluck=True)
    )
    return public[0] if public else None


def get_charts_built_on(query: str) -> list[str]:
    """Charts that read `query`, oldest first.

    A chart reads two: the query the author built, and the `data_query` the
    chart mints for itself. Either link makes the query reachable.
    """
    return frappe.get_all(
        "Insights Chart v3",
        or_filters=[
            ["query", "=", query],
            ["data_query", "=", query],
        ],
        order_by="creation asc",
        pluck="name",
    )


def get_public_permission_user(doctype: str, name: str) -> str | None:
    """The user a public execution of `doctype`/`name` filters its rows by.

    A preview runs as whoever the key was cut for. Everything else runs as the
    user its root recorded when it was published.
    """
    preview = get_preview_key()
    if preview and is_being_previewed(doctype, name):
        return preview["user"]

    root = get_public_root(doctype, name)
    return frappe.db.get_value(*root, "permission_user") if root else None


def is_being_previewed(doctype: str, name: str):
    """Whether this document is part of the dashboard a preview key was cut for.

    The preview browser reads a dashboard, the charts on it and the queries
    behind those charts — the documents the image it produces already shows.
    The key opens those and stops there.
    """
    dashboard = get_previewed_dashboard()
    if not dashboard:
        return False
    if doctype == "Insights Dashboard v3":
        return name == dashboard
    charts = frappe.get_all(
        "Insights Dashboard Chart v3",
        filters={"parent": dashboard, "parenttype": "Insights Dashboard v3"},
        pluck="chart",
    )
    if doctype == "Insights Chart v3":
        return name in charts

    linked = frappe.get_all(
        "Insights Chart v3",
        filters={"name": ["in", charts]},
        fields=["query", "data_query"],
    )
    return any(name in (chart.query, chart.data_query) for chart in linked)


def get_preview_key():
    # used to generate preview images of a dashboard
    key = frappe.request and frappe.request.headers.get("X-Insights-Preview-Key")
    if not key:
        return None
    return frappe.cache.get_value(f"insights_preview_key:{key}")


def get_previewed_dashboard():
    key = get_preview_key()
    return key["dashboard"] if key else None


def is_public_dashboard(name: str):
    return frappe.db.exists(
        "Insights Dashboard v3",
        {
            "name": name,
            "is_public": 1,
        },
    )


@frappe.whitelist(allow_guest=True)
def get_dashboard_name(dashboard_name: str):
    name = dashboard_name
    if not frappe.db.exists("Insights Dashboard v3", name):
        new_name = frappe.db.exists("Insights Dashboard v3", {"old_name": name})
        if new_name:
            name = new_name
    return name


@frappe.whitelist(allow_guest=True)
def get_chart_name(chart_name: str):
    name = chart_name
    if not frappe.db.exists("Insights Chart v3", name):
        new_name = frappe.db.exists("Insights Chart v3", {"old_name": name})
        if new_name:
            name = new_name
    return name
