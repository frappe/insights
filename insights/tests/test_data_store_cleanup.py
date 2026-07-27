import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.utils import add_days, now_datetime

import insights
from insights.insights.doctype.insights_data_source_v3 import data_warehouse
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import open_local_duckdb
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    compact_warehouse,
    drop_orphan_warehouse_tables,
    prune_unused_tables,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.tests.base import InsightsIntegrationTestCase

DATA_SOURCE = "Site DB"


class TestDataStoreCleanup(InsightsIntegrationTestCase):
    def before_test(self):
        frappe.db.delete("Insights Query Execution Log")
        frappe.db.delete("Insights Query Reference")
        frappe.db.delete("Insights Table Import Log")
        self.cutoff = add_days(now_datetime(), -data_warehouse.UNUSED_TABLE_DAYS)

    # helpers

    def create_table(self, table_name, stored=1, sync_mode="Full"):
        name = get_table_name(DATA_SOURCE, table_name)
        if frappe.db.exists("Insights Table v3", name):
            frappe.delete_doc("Insights Table v3", name, force=True)

        doc = frappe.get_doc(
            {
                "doctype": "Insights Table v3",
                "data_source": DATA_SOURCE,
                "table": table_name,
                "label": table_name,
                "stored": stored,
                "sync_mode": sync_mode,
                "last_synced_on": now_datetime(),
            }
        )
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        return doc

    def log_execution(self, query, days_ago):
        log = frappe.get_doc({"doctype": "Insights Query Execution Log", "query": query, "sql": "select 1"})
        log.flags.ignore_links = True
        log.insert(ignore_permissions=True)
        self.backdate("Insights Query Execution Log", log.name, days_ago)

    def log_import(self, table_name, days_ago):
        log = frappe.get_doc(
            {
                "doctype": "Insights Table Import Log",
                "data_source": DATA_SOURCE,
                "table_name": table_name,
                "status": "Completed",
            }
        )
        log.flags.ignore_links = True
        log.insert(ignore_permissions=True)
        self.backdate("Insights Table Import Log", log.name, days_ago)

    def backdate(self, doctype, name, days_ago):
        frappe.db.set_value(
            doctype, name, "creation", add_days(now_datetime(), -days_ago), update_modified=False
        )

    def reference_table(self, query, table_name):
        ref = frappe.get_doc(
            {
                "doctype": "Insights Query Reference",
                "query": query,
                "ref_type": "Table",
                "data_source": DATA_SOURCE,
                "table_name": table_name,
            }
        )
        ref.flags.ignore_links = True
        ref.insert(ignore_permissions=True)

    def reference_query(self, query, ref_query):
        ref = frappe.get_doc(
            {
                "doctype": "Insights Query Reference",
                "query": query,
                "ref_type": "Query",
                "ref_query": ref_query,
            }
        )
        ref.flags.ignore_links = True
        ref.insert(ignore_permissions=True)

    def is_stored(self, table_name):
        return frappe.db.get_value("Insights Table v3", get_table_name(DATA_SOURCE, table_name), "stored")

    # prune

    def test_prunes_table_whose_queries_are_stale(self):
        table = self.create_table("tabCleanupStale")
        self.log_import("tabCleanupStale", days_ago=90)
        self.reference_table("q_stale", "tabCleanupStale")
        self.log_execution("q_stale", days_ago=60)

        pruned = prune_unused_tables(self.cutoff)

        self.assertIn(table.name, pruned)
        self.assertFalse(self.is_stored("tabCleanupStale"))
        self.assertFalse(
            frappe.db.get_value("Insights Table v3", table.name, "last_synced_on"),
            "pruned tables must forget where the last sync stopped",
        )

    def test_keeps_recently_used_table(self):
        self.create_table("tabCleanupUsed")
        self.log_import("tabCleanupUsed", days_ago=90)
        self.reference_table("q_used", "tabCleanupUsed")
        self.log_execution("q_used", days_ago=60)
        self.log_execution("q_used", days_ago=2)

        prune_unused_tables(self.cutoff)

        self.assertTrue(self.is_stored("tabCleanupUsed"))

    def test_keeps_table_used_through_a_nested_query(self):
        self.create_table("tabCleanupNested")
        self.log_import("tabCleanupNested", days_ago=90)
        # only the child query names the table; the parent is what gets executed
        self.reference_table("q_child", "tabCleanupNested")
        self.reference_query("q_parent", "q_child")
        self.log_execution("q_parent", days_ago=2)
        # the site's execution log must reach past the cutoff for pruning to run at all
        self.log_execution("q_other", days_ago=90)

        prune_unused_tables(self.cutoff)

        self.assertTrue(self.is_stored("tabCleanupNested"))

    def test_keeps_freshly_imported_table_nobody_has_queried(self):
        self.create_table("tabCleanupFresh")
        self.log_import("tabCleanupFresh", days_ago=3)
        self.log_execution("q_other", days_ago=90)

        prune_unused_tables(self.cutoff)

        self.assertTrue(self.is_stored("tabCleanupFresh"))

    def test_keeps_incremental_table(self):
        self.create_table("tabCleanupIncremental", sync_mode="Incremental")
        self.log_import("tabCleanupIncremental", days_ago=90)
        self.log_execution("q_other", days_ago=90)

        prune_unused_tables(self.cutoff)

        self.assertTrue(self.is_stored("tabCleanupIncremental"))

    def test_skips_pruning_when_execution_log_was_trimmed(self):
        self.create_table("tabCleanupUnknown")
        self.log_import("tabCleanupUnknown", days_ago=90)
        self.log_execution("q_recent", days_ago=1)

        pruned = prune_unused_tables(self.cutoff)

        self.assertEqual(pruned, [])
        self.assertTrue(self.is_stored("tabCleanupUnknown"))

    # orphan sweep

    @contextmanager
    def warehouse_file(self):
        with tempfile.TemporaryDirectory(prefix="insights_cleanup_test_") as tmpdir:
            path = str(Path(tmpdir) / "insights.duckdb")
            db = open_local_duckdb(path, read_only=False, allowed_dir=tmpdir)
            try:
                yield db, path
            finally:
                try:
                    db.disconnect()
                except Exception:
                    pass

    @contextmanager
    def patched_write_connection(self, db):
        @contextmanager
        def get_write_connection(database=None, timeout=30):
            if database:
                db.raw_sql(f"USE '{database}'")
            yield db

        with patch.object(insights.warehouse, "get_write_connection", get_write_connection):
            yield

    def warehouse_tables(self, db):
        return set(
            db.raw_sql(
                "select schema_name, table_name from duckdb_tables() "
                "where database_name = current_database()"
            ).fetchall()
        )

    def test_orphan_sweep_keeps_stored_tables_and_drops_the_rest(self):
        self.create_table("tabCleanupKept")
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create schema "{schema}"')
            db.raw_sql(f'create table "{schema}".tabcleanupkept as select 1 as a')
            db.raw_sql(f'create table "{schema}".tabcleanupdeleted as select 1 as a')
            db.raw_sql('create schema "gone_data_source"')
            db.raw_sql('create table "gone_data_source".t as select 1 as a')
            db.raw_sql("create table main.site_db_tabcleanuplegacy as select 1 as a")

            with self.patched_write_connection(db):
                dropped = drop_orphan_warehouse_tables()

            self.assertEqual(self.warehouse_tables(db), {(schema, "tabcleanupkept")})
            self.assertIn(f"{schema}.tabcleanupdeleted", dropped)
            self.assertIn("gone_data_source.t", dropped)
            self.assertIn("main.site_db_tabcleanuplegacy", dropped)

            schemas = {row[0] for row in db.raw_sql("select schema_name from duckdb_schemas()").fetchall()}
            self.assertNotIn("gone_data_source", schemas)

    # compaction

    def test_compaction_skipped_for_small_files(self):
        with self.warehouse_file() as (db, path):
            db.raw_sql("create table t as select 1 as a")
            with patch.object(insights.warehouse, "get_db_path", lambda: path):
                self.assertIsNone(compact_warehouse())

    def test_compaction_rebuilds_the_file_and_keeps_data(self):
        with self.warehouse_file() as (db, path):
            db.raw_sql('create schema "s"')
            db.raw_sql('create table "s".keep as select i from range(1000) t(i)')
            # md5 of a random value — incompressible, so the file actually grows
            db.raw_sql('create table "s".dropped as select md5(random()::varchar) as pad from range(200000)')
            db.raw_sql('drop table "s".dropped')
            db.raw_sql("CHECKPOINT")
            db.disconnect()

            with (
                patch.object(insights.warehouse, "get_db_path", lambda: path),
                patch.object(data_warehouse, "COMPACT_MIN_FILE_SIZE", 0),
                patch.object(data_warehouse, "COMPACT_MIN_FREE_RATIO", 0),
            ):
                size_before, size_after = compact_warehouse()

            self.assertEqual(size_after, os.path.getsize(path))
            self.assertLess(size_after, size_before)

            rebuilt = open_local_duckdb(path, read_only=True)
            try:
                self.assertEqual(int(rebuilt.table("keep", database="s").count().execute()), 1000)
            finally:
                rebuilt.disconnect()
