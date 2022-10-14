# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import frappe
import unittest
from insights.tests.utils import create_insights_query

test_dependencies = ["Insights Data Source", "Insights Table"]


class TestQueryStoreDataSource(unittest.TestCase):
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
        db_query = create_insights_query("Test Query", "Test Site DB")
        db_query.append("tables", {"table": "tabUser", "label": "User"})
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
