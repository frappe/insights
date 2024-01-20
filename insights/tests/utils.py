# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from insights.insights.doctype.insights_query.insights_query import InsightsQuery


def before_tests():
    delete_all_records()
    create_query_store()
    create_site_db()
    create_sqlite_db()
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
            }
        )


def delete_all_records():
    frappe.db.delete("Version", {"ref_doctype": ("like", "Insights%")})
    frappe.db.delete("View Log", {"reference_doctype": ("like", "Insights%")})
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


def create_sqlite_db():
    db = frappe.new_doc("Insights Data Source")
    db.title = "Test SQLite DB"
    db.database_type = "SQLite"
    db.database_name = "test_sqlite_db"
    import_todo_table(db)
    db.save()


def import_todo_table(db):
    # need to create todo table for test_insights_query.py
    import pandas as pd

    data = [
        [
            "name",
            "docstatus",
            "description",
            "status",
            "date",
            "owner",
            "modified_by",
            "modified",
            "creation",
        ],
        [
            0,
            0,
            "Test 1",
            "Open",
            "2021-09-01 00:00:00",
            "Administrator",
            "Administrator",
            "2021-09-01 00:00:00",
            "2021-09-01 00:00:00",
        ],
    ]
    df = pd.DataFrame(data[1:], columns=data[0])
    df.to_sql(
        name="tabToDo",
        con=db._db.engine,
        index=False,
        if_exists="replace",
    )


def create_insights_query(title=None, data_source=None) -> InsightsQuery:
    query = frappe.new_doc("Insights Query")
    query.title = title or "Test Query"
    query.data_source = data_source or "Site DB"
    query.save()
    return query
