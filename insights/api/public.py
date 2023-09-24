import frappe


@frappe.whitelist()
def get_public_key(resource_type, resource_name):
    from insights.insights.doctype.insights_chart.insights_chart import (
        get_chart_public_key,
    )
    from insights.insights.doctype.insights_dashboard.insights_dashboard import (
        get_dashboard_public_key,
    )

    if resource_type == "Insights Dashboard":
        return get_dashboard_public_key(resource_name)
    if resource_type == "Insights Chart":
        return get_chart_public_key(resource_name)


@frappe.whitelist(allow_guest=True)
def get_public_dashboard(public_key):
    if not public_key or not isinstance(public_key, str):
        frappe.throw("Public Key is required")

    dashboard_name = frappe.db.exists(
        "Insights Dashboard", {"public_key": public_key, "is_public": 1}
    )
    if not dashboard_name:
        frappe.throw("Invalid Public Key")

    return frappe.get_cached_doc("Insights Dashboard", dashboard_name).as_dict(
        no_default_fields=True
    )


@frappe.whitelist(allow_guest=True)
def get_public_chart(public_key):
    if not public_key or not isinstance(public_key, str):
        frappe.throw("Public Key is required")

    chart_name = frappe.db.exists("Insights Chart", {"public_key": public_key, "is_public": 1})
    if not chart_name:
        frappe.throw("Invalid Public Key")

    chart = frappe.get_cached_doc("Insights Chart", chart_name).as_dict(no_default_fields=True)
    chart_data = frappe.get_cached_doc("Insights Query", chart.query).fetch_results()
    chart["data"] = chart_data
    return chart


@frappe.whitelist(allow_guest=True)
def get_public_dashboard_chart_data(public_key, *args, **kwargs):
    if not public_key or not isinstance(public_key, str):
        frappe.throw("Public Key is required")

    dashboard_name = frappe.db.exists(
        "Insights Dashboard", {"public_key": public_key, "is_public": 1}
    )
    if not dashboard_name:
        frappe.throw("Invalid Public Key")

    kwargs.pop("cmd")
    return frappe.get_cached_doc("Insights Dashboard", dashboard_name).fetch_chart_data(
        *args, **kwargs
    )
