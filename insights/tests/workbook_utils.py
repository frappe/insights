import frappe
from frappe.utils import set_request

from insights.api import get_doc as get_public_doc
from insights.api import run_doc_method as run_public_doc_method
from insights.api.workbooks import create_folder, move_item_to_folder
from insights.tests.factories import (
    as_user,
    create_test_chart,
    create_test_dashboard,
    create_test_query,
    create_test_workbook,
    delete_workbooks,
)


def cleanup_test_workbooks(*owners):
    if owners:
        delete_workbooks(owners=owners)


def get_doc(doctype, name):
    set_request(method="GET", path="/api/method/insights.api.get_doc")
    return get_public_doc(doctype, name)


def run_doc_method(method, doc, args=None):
    set_request(method="POST", path="/api/method/insights.api.run_doc_method")
    return run_public_doc_method(method, doc, args=args)


def get_workbook(name):
    workbook = get_doc("Insights Workbook", name)
    for field in ("folders", "queries", "charts", "dashboards"):
        workbook[field] = frappe.parse_json(workbook.get(field)) or []
    return workbook


def create_workbook_bundle(owner, title, include_secondary_items=False, include_folders=False):
    workbook = create_test_workbook(owner, title=title)
    query = create_test_query(owner, workbook.name, title=f"{title} Query 1")
    chart = create_test_chart(owner, workbook.name, query.name, title=f"{title} Chart 1")
    dashboard = create_test_dashboard(
        owner,
        workbook.name,
        chart.name,
        title=f"{title} Dashboard 1",
    )

    bundle = {
        "workbook": workbook,
        "query": query,
        "chart": chart,
        "dashboard": dashboard,
        "folders": {},
    }

    if include_secondary_items:
        bundle["secondary_query"] = create_test_query(
            owner,
            workbook.name,
            title=f"{title} Query 2",
        )
        bundle["secondary_chart"] = create_test_chart(
            owner,
            workbook.name,
            bundle["secondary_query"].name,
            title=f"{title} Chart 2",
        )

    if include_folders:
        with as_user(owner):
            bundle["folders"]["query"] = create_folder(
                workbook.name,
                f"{title} Query Folder",
                "query",
            )
            bundle["folders"]["chart"] = create_folder(
                workbook.name,
                f"{title} Chart Folder",
                "chart",
            )
            move_item_to_folder("query", query.name, bundle["folders"]["query"])
            move_item_to_folder("chart", chart.name, bundle["folders"]["chart"])

    return bundle
