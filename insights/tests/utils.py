# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe.utils.install import complete_setup_wizard

from insights.insights.doctype.insights_query.insights_query import InsightsQuery


def before_tests():
    complete_setup_wizard()
    frappe.db.commit()


def delete_all_records():
    frappe.db.delete("Version", {"ref_doctype": ("like", "Insights%")})
    frappe.db.delete("View Log", {"reference_doctype": ("like", "Insights%")})
    for doctype in frappe.get_all("DocType", filters={"module": "Insights", "issingle": 0}, pluck="name"):
        frappe.db.delete(doctype)


def create_query_store():
    query_store = frappe.new_doc("Insights Data Source")
    query_store.title = "Query Store"
    query_store.save()


def create_site_db():
    data_source_fixture_path = frappe.get_app_path("insights", "fixtures", "insights_data_source.json")
    with open(data_source_fixture_path) as f:
        site_db = json.load(f)[0]
        frappe.get_doc(site_db).insert()

    data_source_fixture_path = frappe.get_app_path("insights", "fixtures", "insights_data_source_v3.json")
    with open(data_source_fixture_path) as f:
        site_db = json.load(f)[0]
        frappe.get_doc(site_db).insert()


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
