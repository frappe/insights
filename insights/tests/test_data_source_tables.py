import os
from unittest.mock import patch

import duckdb
import frappe
from frappe.utils import get_files_path

from insights.insights.doctype.insights_data_source_v3.connectors.rest_api import RestAPIClient
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT

DATABASE_NAME = "test_new_source_tables"


class TestNewDataSourceTables(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.path = os.path.join(get_files_path(is_private=1), f"{DATABASE_NAME}.duckdb")
        with duckdb.connect(cls.path) as conn:
            conn.execute("create or replace table orders (id integer, amount double)")
            conn.execute("create or replace table customers (id integer, name varchar)")

    @classmethod
    def after_class(cls):
        for name in frappe.get_all(DT.DATA_SOURCE, {"database_name": DATABASE_NAME}, pluck="name"):
            frappe.delete_doc(DT.DATA_SOURCE, name, force=True, ignore_permissions=True)
        frappe.delete_doc_if_exists(DT.DATA_SOURCE, "new_rest_api_source_tables", force=True)
        os.remove(cls.path)

    # @feature data-source.table-list
    def test_a_new_data_source_lists_its_tables(self):
        source = frappe.get_doc(
            {
                "doctype": DT.DATA_SOURCE,
                "title": "New Source Tables",
                "database_type": "DuckDB",
                "database_name": DATABASE_NAME,
            }
        ).insert()

        tables = frappe.get_all(DT.TABLE, {"data_source": source.name}, pluck="table")
        self.assertCountEqual(tables, ["orders", "customers"])

    # @feature data-source.table-list
    def test_a_new_rest_api_source_lists_no_tables(self):
        with patch.object(RestAPIClient, "test_connection"):
            source = frappe.get_doc(
                {
                    "doctype": DT.DATA_SOURCE,
                    "title": "New REST API Source Tables",
                    "type": "REST API",
                    "api_base_url": "https://api.example.com",
                    "schema": "rest_api_source_no_import_yet",
                }
            ).insert()

        self.assertEqual(frappe.get_all(DT.TABLE, {"data_source": source.name}), [])
