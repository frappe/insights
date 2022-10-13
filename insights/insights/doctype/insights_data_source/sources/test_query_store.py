# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import frappe
import unittest


class TestQueryStoreDataSource(unittest.TestCase):
    def tearDown(self) -> None:
        frappe.delete_doc("Insights Data Source", "Test Data Source", force=True)

    def test_duplicate_query_store_creation(self):
        fixtures_path = frappe.get_app_path("insights", "fixtures")
        with open(f"{fixtures_path}/insights_data_source.json") as f:
            QUERY_STORE = json.load(f)
            query_store = frappe.get_doc(QUERY_STORE)
            self.assertRaises(frappe.DuplicateEntryError, query_store.insert)

    def test_query_store_connection(self):
        query_store = frappe.get_doc("Insights Data Source", "Query Store")
        self.assertTrue(query_store.test_connection())

    def test_temporary_table(self):
        # initialize a query
        data_source = create_data_source("Test Data Source", "Database")
        db_query = create_insights_query("Test Query", data_source.name)
        db_query.append("tables", {"table": "tabUser", "label": "ToDo"})
        db_query.save()
        db_query.build_and_execute()
        db_query.save()

        # use query store to query a the above query
        store_query = create_insights_query("Test Store Query", "Query Store")
        store_query.append("tables", {"table": db_query.name, "label": db_query.title})
        store_query.save()
        store_query.build_and_execute()
        store_query.save()
        data = json.loads(store_query.result)
        self.assertEqual(len(data), frappe.db.count("User"))
        # Temporary table should be dropped on closing the connection
        with self.assertRaises(BaseException) as error:
            frappe.db.sql(f"SELECT * FROM `{db_query.name}`")
        self.assertTrue("doesn't exist" in str(error.exception))


def create_data_source(
    title,
    source_type,
    db_type="MariaDB",
    host="localhost",
    port=3306,
    db_name=None,
    username=None,
    password=None,
):
    frappe.delete_doc("Insights Data Source", title, force=True)
    data_source = frappe.new_doc("Insights Data Source")
    data_source.source_type = source_type
    data_source.title = title
    data_source.database_type = db_type
    data_source.host = host
    data_source.port = port
    data_source.database_name = db_name or frappe.conf.db_name
    data_source.username = username or frappe.conf.db_name
    data_source.password = password or frappe.conf.db_password
    data_source.insert()
    return data_source


def create_insights_query(title, data_source):
    query = frappe.new_doc("Insights Query")
    query.title = title or "Test Query"
    query.data_source = data_source
    return query
