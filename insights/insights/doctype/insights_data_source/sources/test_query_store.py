# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import unittest

import frappe

from insights.tests.utils import create_insights_query

test_dependencies = ["Insights Data Source", "Insights Table"]


class TestQueryStoreDataSource(unittest.TestCase):
    def test_temporary_table(self):
        site_db = frappe.get_doc("Insights Data Source", "Site DB")
        site_db.sync_tables(tables=["tabUser"])
        # initialize a query
        db_query = create_insights_query("Test Query", "Site DB")
        db_query.append("tables", {"table": "tabUser", "label": "User"})
        db_query.append(
            "columns",
            {
                "label": "Name",
                "column": "name",
                "table": "tabUser",
                "type": "String",
            },
        )
        db_query.is_stored = 1
        db_query.run()

        store_query = create_insights_query("Test Store Query", "Query Store")
        store_query.append("tables", {"table": db_query.name, "label": db_query.title})
        store_query.save()
        store_query.run()
        data = frappe.parse_json(store_query.results)[1:]
        self.assertEqual(len(data), frappe.db.count("User"))
        # Temporary table should be dropped on closing the connection
        with self.assertRaises(Exception) as error:
            frappe.db.sql(f"SELECT * FROM `{db_query.name}`")
        self.assertTrue("doesn't exist" in str(error.exception))
