import frappe

CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"


def execute():
    """
    Public content runs with its owner's permissions, so content already
    published with `apply_user_permissions` checked drew an empty page for the
    guests it was published for.

    A chart reaches a guest two ways - on its own level, or through a Public
    dashboard it is linked to - and both are named here, because the update that
    names them from now on runs on the dashboard's save.
    """
    charts = set(frappe.get_all(CHART, filters={"visibility": "Public"}, pluck="name"))

    published_dashboards = frappe.get_all(DASHBOARD, filters={"visibility": "Public"}, pluck="name")
    if published_dashboards:
        charts.update(
            frappe.get_all(
                "Insights Dashboard Chart v3",
                filters={"parenttype": DASHBOARD, "parent": ("in", published_dashboards)},
                pluck="chart",
            )
        )

    for chart in charts:
        frappe.db.set_value(CHART, chart, "apply_user_permissions", 0, update_modified=False)
