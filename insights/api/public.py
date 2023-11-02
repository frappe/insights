import frappe
from frappe.utils.caching import redis_cache

from insights.api.data_sources import fetch_column_values


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


@frappe.whitelist(allow_guest=True)
@redis_cache()
def fetch_column_values_public(public_key, item_id, search_text=None):
    if not public_key or not isinstance(public_key, str):
        frappe.throw("Public Key is required")

    dashboard_name = frappe.db.exists(
        "Insights Dashboard", {"public_key": public_key, "is_public": 1}
    )
    if not dashboard_name:
        frappe.throw("Invalid Public Key")

    doc = frappe.get_doc("Insights Dashboard", dashboard_name)
    row = next((row for row in doc.items if row.item_id == item_id), None)
    if not row:
        frappe.throw("Invalid Item ID")

    options = frappe.parse_json(row.options)
    column = options.get("column")
    if not column:
        frappe.throw("Column not found in Item Options")

    return fetch_column_values(
        data_source=column.get("data_source"),
        table=column.get("table"),
        column=column.get("column"),
        search_text=search_text,
    )
