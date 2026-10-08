"""What an admin may give back from the data store, and what stops them.

A column is read when a query, chart, dashboard filter or alert on its table
names it. Only an unread column may be skipped, and a skipped column leaves
the table's column list. The storage overview puts every byte of the file in
one group.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.utils import add_days, now_datetime

import insights
from insights.api.data_store import get_storage
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import open_local_duckdb
from insights.insights.doctype.insights_data_source_v3.data_store_storage import measure_data_store
from insights.insights.doctype.insights_table_v3.column_usage import get_column_readers
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    get_stored_columns,
    get_table_name,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_chart, create_test_query, create_test_workbook
from insights.tests.permissions_utils import (
    TEST_DS,
    TEST_TABLE1,
    TEST_TABLE2_NAME,
    USER_1,
    cleanup_test_fixtures,
    create_test_data_sources,
    create_test_tables,
    create_test_users,
)

IMPORT_LOG = "Insights Table Import Log"
COLUMNS = ["description", "category", "region", "amount", "discount", "untouched"]


def source(table="table1"):
    return {"type": "source", "table": {"type": "table", "data_source": TEST_DS, "table_name": table}}


class TestColumnReaders(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cleanup_test_fixtures()
        create_test_users()
        create_test_data_sources()
        create_test_tables()
        workbook = create_test_workbook("Administrator").name

        cls.base = create_test_query("Administrator", workbook, "Whole Table", [source()]).name
        cls.on_base = create_test_query(
            "Administrator",
            workbook,
            "By Category",
            [
                {"type": "source", "table": {"type": "query", "workbook": 0, "query_name": cls.base}},
                {
                    "type": "filter",
                    "column": {"type": "column", "column_name": "category"},
                    "operator": "=",
                    "value": "Books",
                },
            ],
        ).name
        cls.chart = create_test_chart(
            "Administrator",
            workbook,
            query=cls.base,
            title="By Region",
            config={"x_axis": {"dimension": {"column_name": "region", "dimension_name": "Region"}}},
        ).name
        cls.native = create_test_query(
            "Administrator",
            workbook,
            "Native Amount",
            [{"type": "sql", "raw_sql": "select sum(amount) from table1", "data_source": TEST_DS}],
        ).name
        cls.expression = create_test_query(
            "Administrator",
            workbook,
            "Discounted",
            [
                source(),
                {
                    "type": "mutate",
                    "new_name": "half",
                    "data_type": "Decimal",
                    "expression": {"type": "expression", "expression": "discount * 0.5"},
                },
            ],
        ).name

    @classmethod
    def after_class(cls):
        cleanup_test_fixtures()

    def readers(self, column):
        return {r["name"] for r in get_column_readers(TEST_DS, "table1", COLUMNS)[column]}

    def skip(self, table, columns):
        self.addCleanup(frappe.db.set_value, DT.TABLE, table, "skipped_columns", None)
        frappe.get_doc(DT.TABLE, table).skip_columns(columns)

    # @feature data-store.column-readers
    def test_a_query_built_on_a_query_reads_the_columns_it_names(self):
        self.assertEqual(self.readers("category"), {self.on_base})

    # @feature data-store.column-readers
    def test_a_query_with_no_projection_reads_no_column(self):
        readers = get_column_readers(TEST_DS, "table1", COLUMNS)
        self.assertEqual(readers["untouched"], [])
        self.assertFalse(any(r["name"] == self.base for found in readers.values() for r in found))

    # @feature data-store.column-readers
    def test_a_chart_reads_the_columns_its_config_names(self):
        self.assertEqual(self.readers("region"), {self.chart})

    # @feature data-store.column-readers
    def test_native_sql_and_an_expression_read_the_columns_they_name(self):
        self.assertEqual(self.readers("amount"), {self.native})
        self.assertEqual(self.readers("discount"), {self.expression})

    # @feature data-store.skip-unread-column
    def test_skipping_a_column_a_query_reads_is_refused_and_names_the_query(self):
        with self.assertRaises(frappe.ValidationError) as refused:
            self.skip(TEST_TABLE1, ["category"])
        self.assertIn("By Category", str(refused.exception))
        self.assertIsNone(frappe.db.get_value(DT.TABLE, TEST_TABLE1, "skipped_columns"))

    # @feature data-store.skip-unread-column
    def test_a_skipped_column_leaves_the_stored_column_list(self):
        frappe.db.set_value(
            DT.TABLE,
            TEST_TABLE1,
            "columns",
            frappe.as_json(
                [{"name": "description", "type": "String"}, {"name": "untouched", "type": "String"}]
            ),
        )
        self.addCleanup(frappe.db.set_value, DT.TABLE, TEST_TABLE1, "columns", None)

        self.skip(TEST_TABLE1, ["untouched"])

        columns = get_stored_columns(TEST_DS)[TEST_TABLE1].columns
        self.assertEqual([c["name"] for c in columns], ["description"])

    # @feature data-store.skip-unread-column
    def test_skipping_the_incremental_cursor_is_refused(self):
        frappe.db.set_value(
            DT.TABLE, TEST_TABLE2_NAME, {"sync_mode": "Incremental", "sync_cursor_column": "description"}
        )
        self.addCleanup(
            frappe.db.set_value, DT.TABLE, TEST_TABLE2_NAME, {"sync_mode": "Full", "sync_cursor_column": None}
        )

        with self.assertRaises(frappe.ValidationError) as refused:
            self.skip(TEST_TABLE2_NAME, ["description"])
        self.assertIn("incremental sync", str(refused.exception))

    # @feature data-store.skip-unread-column
    def test_a_non_admin_cannot_skip_a_column(self):
        with self.as_user(USER_1), self.assertRaises(frappe.PermissionError):
            self.skip(TEST_TABLE1, ["untouched"])


class TestStorageOverview(InsightsIntegrationTestCase):
    DATA_SOURCE = "Site DB"
    TABLE = "tabSpaceOverview"

    @classmethod
    def before_class(cls):
        create_test_users()
        name = get_table_name(cls.DATA_SOURCE, cls.TABLE)
        if frappe.db.exists(DT.TABLE, name):
            frappe.delete_doc(DT.TABLE, name, force=True)
        doc = frappe.get_doc(
            {
                "doctype": DT.TABLE,
                "data_source": cls.DATA_SOURCE,
                "table": cls.TABLE,
                "label": cls.TABLE,
                "stored": 1,
            }
        )
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.TABLE, get_table_name(cls.DATA_SOURCE, cls.TABLE), force=True)

    @contextmanager
    def measured_warehouse(self):
        with tempfile.TemporaryDirectory(prefix="insights_space_test_") as folder:
            path = str(Path(folder) / "insights.duckdb")
            db = open_local_duckdb(path, read_only=False, allowed_dir=folder)

            @contextmanager
            def get_write_connection(database=None, timeout=30):
                yield db

            try:
                db.raw_sql('create schema "site_db"')
                db.raw_sql(
                    'create table "site_db".tabspaceoverview as '
                    "select i as id, repeat('x', 3000) || i::varchar as body from range(500) t(i)"
                )
                db.raw_sql(
                    'create table "site_db".ibis_duckdb_table_abc as '
                    "select repeat('y', 3000) || i::varchar as body from range(300) t(i)"
                )
                with (
                    patch.object(insights.warehouse, "get_db_path", lambda: path),
                    patch.object(insights.warehouse, "get_write_connection", get_write_connection),
                ):
                    measure_data_store()
                    yield
            finally:
                db.disconnect()

    # @feature data-store.storage-breakdown
    def test_the_groups_add_up_to_the_file(self):
        with self.measured_warehouse():
            storage = get_storage()

        self.assertEqual(sum(storage["groups"].values()), storage["file_bytes"])
        self.assertEqual([t["table"] for t in storage["tables"]], [self.TABLE])
        self.assertEqual(
            [(t["schema"], t["table"]) for t in storage["leftover_tables"]],
            [("site_db", "ibis_duckdb_table_abc")],
        )
        self.assertEqual(storage["groups"]["leftover"], storage["leftover_tables"][0]["bytes"])

    # @feature data-store.give-back
    def test_a_table_not_read_in_the_window_is_unread_unless_first_imported_inside_it(self):
        for days_ago, unread in ((60, True), (5, False)):
            with self.subTest(imported_days_ago=days_ago):
                self.log_import(days_ago)
                with self.measured_warehouse():
                    storage = get_storage()

                self.assertTrue(storage["usage_known"])
                self.assertEqual([t["unread"] for t in storage["tables"]], [unread])

    def log_import(self, days_ago):
        frappe.db.delete(IMPORT_LOG, {"data_source": self.DATA_SOURCE, "table_name": self.TABLE})
        log = frappe.get_doc(
            {
                "doctype": IMPORT_LOG,
                "data_source": self.DATA_SOURCE,
                "table_name": self.TABLE,
                "status": "Completed",
            }
        )
        log.flags.ignore_links = True
        log.insert(ignore_permissions=True)
        frappe.db.set_value(
            IMPORT_LOG, log.name, "creation", add_days(now_datetime(), -days_ago), update_modified=False
        )

    # @feature data-store.storage-breakdown
    def test_a_non_admin_cannot_read_the_storage(self):
        with self.as_user(USER_1), self.assertRaises(frappe.PermissionError):
            get_storage()
