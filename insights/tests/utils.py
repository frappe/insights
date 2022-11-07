# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from insights.insights.doctype.insights_query.insights_query import InsightsQuery


def before_tests():
    delete_all_records()
    create_query_store()
    create_site_db()
    complete_setup_wizard()
    frappe.db.commit()


def complete_setup_wizard():
    frappe.clear_cache()
    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

    if not frappe.db.get_single_value("System Settings", "setup_complete"):
        setup_complete(
            {
                "language": "English",
                "email": "test@erpnext.com",
                "full_name": "Test User",
                "password": "test",
                "country": "United States",
                "timezone": "America/New_York",
                "currency": "USD",
                "setup_demo_db": 1,
            }
        )


def delete_all_records():
    for doctype in frappe.get_all(
        "DocType", filters={"module": "Insights", "issingle": 0}, pluck="name"
    ):
        frappe.db.delete(doctype)


def create_query_store():
    query_store = frappe.new_doc("Insights Data Source")
    query_store.title = "Query Store"
    query_store.save()


def create_site_db():
    site_db = frappe.new_doc("Insights Data Source")
    site_db.title = "Site DB"
    site_db.is_site_db = 1
    site_db.save()


def create_insights_query(title=None, data_source=None) -> InsightsQuery:
    query = frappe.new_doc("Insights Query")
    query.title = title or "Test Query"
    query.data_source = data_source or "Site DB"
    query.save()
    return query
