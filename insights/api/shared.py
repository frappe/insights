import frappe

from insights.decorators import validate_type


def is_shared(doctype: str, name: str):
    if doctype == "Insights Workbook":
        return is_shared_workbook(name)
    if doctype == "Insights Dashboard v3":
        return is_shared_dashboard(name)
    if doctype == "Insights Chart v3":
        return is_shared_chart(name)
    if doctype == "Insights Query v3":
        return is_shared_query(name)

    return False


@validate_type
def is_shared_workbook(name: str):
    shared_dashboard_exists = frappe.db.exists(
        "Insights Dashboard v3",
        {
            "workbook": name,
            "is_public": 1,
        },
    )
    if shared_dashboard_exists:
        return True

    shared_charts = get_shared_charts()
    return frappe.db.exists(
        "Insights Chart v3",
        {
            "workbook": name,
            "name": ["in", shared_charts],
        },
    )


@validate_type
def is_shared_dashboard(name: str):
    return frappe.db.exists(
        "Insights Dashboard v3",
        {
            "name": name,
            "is_public": 1,
        },
    )


def get_shared_charts():
    charts = frappe.get_all(
        "Insights Chart v3",
        filters={"is_public": 1},
        pluck="name",
    )

    linked_public_charts = frappe.get_all(
        "Insights Dashboard v3",
        filters={"is_public": 1},
        pluck="linked_charts",
    )
    for charts in linked_public_charts:
        charts.extend(frappe.parse_json(charts))

    return list(set(charts))


@validate_type
def is_shared_chart(name: str):
    is_public = frappe.db.exists(
        "Insights Chart v3",
        {
            "name": name,
            "is_public": 1,
        },
    )
    if is_public:
        return True

    return name in get_shared_charts()


@validate_type
def is_shared_query(name: str):
    # find a shared chart that is linked with this query
    linked_charts = frappe.get_all(
        "Insights Chart v3",
        or_filters=[
            ["query", "=", name],
            ["data_query", "=", name],
        ],
        pluck="name",
    )
    shared_charts = get_shared_charts()
    if any(chart in shared_charts for chart in linked_charts):
        return True

    return False
