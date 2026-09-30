import os

import duckdb
import frappe
from frappe.utils import get_files_path

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
