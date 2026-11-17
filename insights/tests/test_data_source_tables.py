import os
from unittest.mock import patch

import duckdb
import frappe
from frappe.utils import get_files_path

from insights.insights.doctype.insights_data_source_v3.connectors.frappe_db import get_primary_data_source
from insights.insights.doctype.insights_data_source_v3.connectors.rest_api import RestAPIClient
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT

DATABASE_NAME = "test_new_source_tables"
CHANGED_DATABASE_NAME = "test_changed_source_tables"


class TestNewDataSourceTables(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.path = os.path.join(get_files_path(is_private=1), f"{DATABASE_NAME}.duckdb")
        with duckdb.connect(cls.path) as conn:
            conn.execute("create or replace table orders (id integer, amount double)")
            conn.execute("create or replace table customers (id integer, name varchar)")
        cls.changed_path = os.path.join(get_files_path(is_private=1), f"{CHANGED_DATABASE_NAME}.duckdb")
        with duckdb.connect(cls.changed_path) as conn:
            conn.execute("create or replace table invoices (id integer, total double)")

    @classmethod
    def after_class(cls):
        for name in frappe.get_all(
            DT.DATA_SOURCE,
            {"database_name": ("in", [DATABASE_NAME, CHANGED_DATABASE_NAME])},
            pluck="name",
        ):
            frappe.delete_doc(DT.DATA_SOURCE, name, force=True, ignore_permissions=True)
        for name in ("new_rest_api_source_tables", "site_database_by_credentials"):
            frappe.delete_doc_if_exists(DT.DATA_SOURCE, name, force=True)
        os.remove(cls.path)
        os.remove(cls.changed_path)

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
    def test_a_saved_data_source_lists_its_new_tables_when_its_database_changes(self):
        # the save is a later request, so it does not reuse the insert's connection
        with db_connections():
            source = frappe.get_doc(
                {
                    "doctype": DT.DATA_SOURCE,
                    "title": "Changed Source Tables",
                    "database_type": "DuckDB",
                    "database_name": DATABASE_NAME,
                }
            ).insert()

        source.database_name = CHANGED_DATABASE_NAME
        source.save()

        tables = frappe.get_all(DT.TABLE, {"data_source": source.name}, pluck="table")
        self.assertIn("invoices", tables)

    # @feature data-source.connect-mariadb
    def test_a_new_mariadb_source_on_a_frappe_database_is_marked_as_one(self):
        site = get_primary_data_source()
        source = frappe.get_doc(
            {
                "doctype": DT.DATA_SOURCE,
                "title": "Site Database By Credentials",
                "database_type": site.database_type,
                "host": site.host,
                "port": site.port,
                "database_name": site.database_name,
                "username": site.username,
                "password": site.password,
            }
        ).insert()

        self.assertEqual(source.status, "Active")
        self.assertTrue(frappe.db.get_value(DT.DATA_SOURCE, source.name, "is_frappe_db"))

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
