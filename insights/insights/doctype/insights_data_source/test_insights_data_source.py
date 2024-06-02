# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from ibis import _

from .insights_data_source import InsightsDataSource, build_ibis_query


class TestInsightsDataSource(FrappeTestCase):
    def get_data_source(self) -> InsightsDataSource:
        if not frappe.db.exists("Insights Data Source", "sales"):
            doc = frappe.get_doc(
                {
                    "doctype": "Insights Data Source",
                    "title": "sales",
                    "database_type": "MariaDB",
                    "host": "localhost",
                    "port": "3306",
                    "database_name": "sales",
                    "username": "demouser",
                    "password": "demouser",
                }
            )
            doc.insert()
        return frappe.get_doc("Insights Data Source", "sales")

    def test_connection(self):
        ds = self.get_data_source()
        ds.test_connection(raise_exception=True)

    def test_sync_tables(self):
        ds = self.get_data_source()
        ds.sync_tables()
        count = frappe.db.count("Insights Table", {"data_source": "sales"})
        self.assertGreater(count, 0)

    def test_execute_query(self):
        ds = self.get_data_source()
        res = ds.execute_query(
            ds.get_db_table("transactions").aggregate(
                total_sales=_.sales_amount.sum(),
                by="customer_code",
            )
        )
        self.assertGreater(len(res), 0)

    def test_copy_table(self):
        ds = self.get_data_source()
        ds.create_parquet_file("transactions")
