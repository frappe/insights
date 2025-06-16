import frappe
from frappe.query_builder import DocType

from insights.decorators import validate_type

public_doctypes = [
    "Insights Dashboard v3",
    "Insights Chart v3",
    "Insights Query v3",
]


def check_public_access(doctype, name):
    if frappe.session.user != "Guest":
        return
    if doctype not in public_doctypes or not is_public(doctype, name):
        raise frappe.PermissionError("You don't have permission to access this document")


def is_public(doctype: str, name: str):
    if has_valid_preview_key():
        return True
    if doctype == "Insights Workbook":
        return is_public_workbook(name)
    if doctype == "Insights Dashboard v3":
        return is_public_dashboard(name)
    if doctype == "Insights Chart v3":
        return is_public_chart(name)
    if doctype == "Insights Query v3":
        return is_public_query(name)

    return False


@validate_type
def is_public_workbook(name: str):
    public_dashboard_exists = frappe.db.exists(
        "Insights Dashboard v3",
        {
            "workbook": name,
            "is_public": 1,
        },
    )
    if public_dashboard_exists:
        return True

    public_charts = get_public_charts()
    return frappe.db.exists(
        "Insights Chart v3",
        {
            "workbook": name,
            "name": ["in", public_charts],
        },
    )


def has_valid_preview_key():
    # used to generate preview images of a dashboard
    preview_key = frappe.request.headers.get("X-Insights-Preview-Key")
    return preview_key and frappe.cache.get_value(f"insights_preview_key:{preview_key}")


@validate_type
def is_public_dashboard(name: str):
    return frappe.db.exists(
        "Insights Dashboard v3",
        {
            "name": name,
            "is_public": 1,
        },
    )


def get_public_charts():
    Chart = DocType("Insights Chart v3")
    Dashboard = DocType("Insights Dashboard v3")
    DashboardChart = DocType("Insights Dashboard Chart v3")

    public_dashboards = frappe.qb.from_(Dashboard).select(Dashboard.name).where(Dashboard.is_public == 1)

    charts = (
        frappe.qb.from_(Chart)
        .select(Chart.name)
        .where(
            (Chart.is_public == 1)
            | (
                Chart.name.isin(
                    frappe.qb.from_(DashboardChart)
                    .select(DashboardChart.chart)
                    .where(DashboardChart.parent.isin(public_dashboards))
                )
            )
        )
        .run(pluck=True)
    )

    return list(set(charts))


@validate_type
def is_public_chart(name: str):
    is_public = frappe.db.exists(
        "Insights Chart v3",
        {
            "name": name,
            "is_public": 1,
        },
    )
    if is_public:
        return True

    return name in get_public_charts()


@validate_type
def is_public_query(name: str):
    # find a public chart that is linked with this query
    linked_charts = frappe.get_all(
        "Insights Chart v3",
        or_filters=[
            ["query", "=", name],
            ["data_query", "=", name],
        ],
        pluck="name",
    )
    public_charts = get_public_charts()
    if any(chart in public_charts for chart in linked_charts):
        return True

    return False


@frappe.whitelist(allow_guest=True)
@validate_type
def get_dashboard_name(dashboard_name: str):
    name = dashboard_name
    if not frappe.db.exists("Insights Dashboard v3", name):
        new_name = frappe.db.exists("Insights Dashboard v3", {"old_name": name})
        if new_name:
            name = new_name
    return name


@frappe.whitelist(allow_guest=True)
@validate_type
def get_chart_name(chart_name: str):
    name = chart_name
    if not frappe.db.exists("Insights Chart v3", name):
        new_name = frappe.db.exists("Insights Chart v3", {"old_name": name})
        if new_name:
            name = new_name
    return name
