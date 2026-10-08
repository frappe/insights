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
from insights.insights.doctype.insights_data_source_v3.data_store_storage import (
    get_storage,
    measure_data_store,
    measure_table,
    record_table_storage,
)
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
        self.set_retention(90)

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

    def create_import_job(self, table_name):
        if frappe.db.exists("Insights Table Import Job", table_name):
            frappe.delete_doc("Insights Table Import Job", table_name, force=True)

        doc = frappe.get_doc(
            {
                "doctype": "Insights Table Import Job",
                "title": table_name,
                "data_source": DATA_SOURCE,
                "table_name": table_name,
                "script": "pass",
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

    def set_retention(self, days):
        """Set the execution log's row in Log Settings; `None` deletes the row, as before Log Settings is first saved after migrate."""
        doctype = "Insights Query Execution Log"
        log_settings = frappe.get_doc("Log Settings")
        original = next((row.days for row in log_settings.logs_to_clear if row.ref_doctype == doctype), None)
        self.addCleanup(self.write_retention, original)
        self.write_retention(days)

    def write_retention(self, days):
        doctype = "Insights Query Execution Log"
        if days is None:
            frappe.db.delete("Logs To Clear", {"parent": "Log Settings", "ref_doctype": doctype})
            return
        log_settings = frappe.get_doc("Log Settings")
        log_settings.logs_to_clear = [row for row in log_settings.logs_to_clear if row.ref_doctype != doctype]
        log_settings.register_doctype(doctype, days)
        log_settings.save(ignore_permissions=True)

    def is_stored(self, table_name):
        return frappe.db.get_value("Insights Table v3", get_table_name(DATA_SOURCE, table_name), "stored")

    # prune

    # @feature data-store.cleanup-prunes-stale
    def test_prunes_table_whose_queries_are_stale(self):
        table = self.create_table("tabCleanupStale")
        self.log_import("tabCleanupStale", days_ago=90)
        self.reference_table("q_stale", "tabCleanupStale")
        self.log_execution("q_stale", days_ago=60)

        pruned = prune_unused_tables()

        self.assertIn(table.name, pruned)
        self.assertFalse(self.is_stored("tabCleanupStale"))
        self.assertFalse(
            frappe.db.get_value("Insights Table v3", table.name, "last_synced_on"),
            "pruned tables must forget where the last sync stopped",
        )

    # @feature data-store.cleanup-prunes-stale
    def test_keeps_recently_used_table(self):
        self.create_table("tabCleanupUsed")
        self.log_import("tabCleanupUsed", days_ago=90)
        self.reference_table("q_used", "tabCleanupUsed")
        self.log_execution("q_used", days_ago=60)
        self.log_execution("q_used", days_ago=2)

        prune_unused_tables()

        self.assertTrue(self.is_stored("tabCleanupUsed"))

    # @feature data-store.cleanup-prunes-stale
    def test_keeps_table_used_through_a_nested_query(self):
        self.create_table("tabCleanupNested")
        self.log_import("tabCleanupNested", days_ago=90)
        # only the child query names the table; the parent is what gets executed
        self.reference_table("q_child", "tabCleanupNested")
        self.reference_query("q_parent", "q_child")
        self.log_execution("q_parent", days_ago=2)

        prune_unused_tables()

        self.assertTrue(self.is_stored("tabCleanupNested"))

    # @feature data-store.cleanup-prunes-stale
    def test_keeps_freshly_imported_table_nobody_has_queried(self):
        self.create_table("tabCleanupFresh")
        self.log_import("tabCleanupFresh", days_ago=3)

        prune_unused_tables()

        self.assertTrue(self.is_stored("tabCleanupFresh"))

    # @feature data-store.cleanup-prunes-stale
    def test_keeps_incremental_table(self):
        self.create_table("tabCleanupIncremental", sync_mode="Incremental")
        self.log_import("tabCleanupIncremental", days_ago=90)

        prune_unused_tables()

        self.assertTrue(self.is_stored("tabCleanupIncremental"))

    # @feature data-store.cleanup-prunes-stale
    def test_prunes_unused_table_when_the_retention_emptied_the_log(self):
        for days in (90, data_warehouse.UNUSED_TABLE_DAYS, None):
            with self.subTest(retention=days):
                self.set_retention(days)
                table = self.create_table("tabCleanupIdle")
                self.log_import("tabCleanupIdle", days_ago=60)

                self.assertIn(table.name, prune_unused_tables())

    # @feature data-store.cleanup-prunes-stale
    def test_skips_pruning_when_retention_is_shorter_than_the_unused_window(self):
        self.set_retention(10)
        self.create_table("tabCleanupUnknown")
        self.log_import("tabCleanupUnknown", days_ago=90)
        self.log_execution("q_recent", days_ago=1)

        pruned = prune_unused_tables()

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

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_keeps_stored_tables_and_drops_empty_orphans(self):
        self.create_table("tabCleanupKept")
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create schema "{schema}"')
            db.raw_sql(f'create table "{schema}".tabcleanupkept as select 1 as a')
            db.raw_sql(f'create table "{schema}".tabcleanupdeleted as select 1 as a where false')
            db.raw_sql('create schema "gone_data_source"')
            db.raw_sql('create table "gone_data_source".t as select 1 as a where false')
            db.raw_sql("create table main.site_db_tabcleanuplegacy as select 1 as a where false")

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(self.warehouse_tables(db), {(schema, "tabcleanupkept")})
            self.assertIn(f"{schema}.tabcleanupdeleted", dropped)
            self.assertIn("gone_data_source.t", dropped)
            self.assertIn("main.site_db_tabcleanuplegacy", dropped)
            self.assertEqual(kept, [])

            schemas = {row[0] for row in db.raw_sql("select schema_name from duckdb_schemas()").fetchall()}
            self.assertNotIn("gone_data_source", schemas)

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_keeps_an_unexplained_table_holding_rows(self):
        """The bug behind frappe/insights#1295: a writer that never set `stored`."""
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create schema "{schema}"')
            db.raw_sql(f'create table "{schema}".tabcleanuporphan as select 1 as a')

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [])
            self.assertEqual(kept, [f"{schema}.tabcleanuporphan"])
            self.assertIn((schema, "tabcleanuporphan"), self.warehouse_tables(db))

        self.assertTrue(
            frappe.db.exists("Error Log", {"method": "Data store cleanup kept an unexplained table"}),
            "a table the sweep refuses to drop must leave a record that outlives the file log",
        )

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_drops_a_pruned_table_holding_rows(self):
        """A pruned table is not unexplained: its doc says a re-import rebuilds it."""
        self.create_table("tabCleanupPruned", stored=0)
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create schema "{schema}"')
            db.raw_sql(f'create table "{schema}".tabcleanuppruned as select 1 as a')

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [f"{schema}.tabcleanuppruned"])
            self.assertEqual(kept, [])

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_keeps_a_pruned_incremental_table_holding_rows(self):
        """An incremental re-import restarts from `sync_from`, so it rebuilds nothing."""
        self.create_table("tabCleanupPrunedInc", stored=0, sync_mode="Incremental")
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create schema "{schema}"')
            db.raw_sql(f'create table "{schema}".tabcleanupprunedinc as select 1 as a')

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [])
            self.assertEqual(kept, [f"{schema}.tabcleanupprunedinc"])

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_drops_a_legacy_flat_table_its_successor_replaced(self):
        """`main."site_db.tabX"` is the pre-rename copy of `site_db.tabx`."""
        self.create_table("tabCleanupFlat")
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create schema "{schema}"')
            db.raw_sql(f'create table "{schema}".tabcleanupflat as select 1 as a')
            db.raw_sql(f'create table main."{schema}.tabCleanupFlat" as select 1 as a')

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [f"main.{schema}.tabCleanupFlat"])
            self.assertEqual(kept, [])

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_keeps_a_legacy_flat_table_with_no_successor(self):
        """Nothing replaced it, so its rows may be the only copy."""
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create table main."{schema}.tabCleanupLost" as select 1 as a')

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [])
            self.assertEqual(kept, [f"main.{schema}.tabCleanupLost"])

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_keeps_a_flat_table_it_cannot_attribute(self):
        """No data source claims this prefix, so the split cannot name a successor."""
        with self.warehouse_file() as (db, _):
            db.raw_sql('create table main."tabCleanupUnowned" as select 1 as a')

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [])
            self.assertEqual(kept, ["main.tabCleanupUnowned"])

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_keeps_the_table_an_import_job_writes(self):
        # A job writes to the source's `schema` field, not to the derived name.
        frappe.db.set_value("Insights Data Source v3", DATA_SOURCE, "schema", "job_schema")
        self.create_import_job("cleanup_job_table")

        with self.warehouse_file() as (db, _):
            db.raw_sql('create schema "job_schema"')
            db.raw_sql('create table "job_schema".cleanup_job_table as select 1 as a')

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [])
            self.assertEqual(kept, [], "a known import job table is explained, so it raises no alarm")
            self.assertIn(("job_schema", "cleanup_job_table"), self.warehouse_tables(db))

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_drops_a_leftover_table_a_live_table_holds(self):
        """A dead import left `ibis_duckdb_table_*`; the live table has been re-imported since."""
        self.create_table("tabCleanupLive")
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)
        leftover = "ibis_duckdb_table_cleanuplive"

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create schema "{schema}"')
            db.raw_sql(f'create table "{schema}".tabcleanuplive as select i as a, i as b from range(3) t(i)')
            db.raw_sql(f'create table "{schema}".{leftover} as select i as b, i as a from range(3) t(i)')

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [f"{schema}.{leftover}"])
            self.assertEqual(kept, [])
            self.assertEqual(self.warehouse_tables(db), {(schema, "tabcleanuplive")})

    # @feature data-store.cleanup-keeps-unexplained
    def test_orphan_sweep_keeps_a_leftover_table_no_live_table_holds(self):
        """More rows than the live table, or other columns: the leftover may hold rows nothing else does."""
        self.create_table("tabCleanupLive")
        schema = data_warehouse.get_warehouse_schema_name(DATA_SOURCE)

        with self.warehouse_file() as (db, _):
            db.raw_sql(f'create schema "{schema}"')
            db.raw_sql(f'create table "{schema}".tabcleanuplive as select i as a, i as b from range(3) t(i)')
            db.raw_sql(
                f'create table "{schema}".ibis_duckdb_table_more as select i as a, i as b from range(4) t(i)'
            )
            db.raw_sql(
                f'create table "{schema}".ibis_duckdb_table_other as select i as a, i as c from range(2) t(i)'
            )

            with self.patched_write_connection(db):
                dropped, kept = drop_orphan_warehouse_tables()

            self.assertEqual(dropped, [])
            self.assertEqual(
                sorted(kept), [f"{schema}.ibis_duckdb_table_more", f"{schema}.ibis_duckdb_table_other"]
            )

    # @feature data-store.cleanup-legacy-parquet
    def test_cleanup_deletes_the_parquet_files_the_store_kept_before_duckdb(self):
        with self.warehouse_file() as (db, path):
            folder = Path(path).parent
            db.raw_sql(f"copy (select 1 as a) to '{folder / 'site_db.tabtodo.parquet'}' (format parquet)")
            (folder / "storage.json").write_text("{}")

            with patch.object(insights.warehouse, "get_db_path", lambda: path):
                deleted = data_warehouse.delete_legacy_parquet_files()

            self.assertEqual(deleted, ["site_db.tabtodo.parquet"])
            self.assertEqual(
                sorted(p.name for p in folder.iterdir() if not p.name.startswith("insights.duckdb")),
                ["storage.json"],
            )

    # compaction

    # @feature data-store.compaction
    def test_compaction_skipped_for_small_files(self):
        with self.warehouse_file() as (db, path):
            db.raw_sql("create table t as select 1 as a")
            with patch.object(insights.warehouse, "get_db_path", lambda: path):
                self.assertIsNone(compact_warehouse())

    # @feature data-store.compaction
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

    # measurement

    @contextmanager
    def measured_warehouse(self):
        with self.warehouse_file() as (db, path):
            with (
                patch.object(insights.warehouse, "get_db_path", lambda: path),
                self.patched_write_connection(db),
            ):
                yield db

    def create_wide_table(self, db, schema, table, rows=2000):
        db.raw_sql(f'create schema if not exists "{schema}"')
        # 5 KB strings overflow into blocks of their own; the two integer
        # columns are small enough to share a block with the string column.
        db.raw_sql(
            f'create or replace table "{schema}"."{table}" as '
            "select i, repeat('x', 5000) || i::varchar as body, i % 3 as bucket "
            f"from range({rows}) t(i)"
        )

    def used_bytes(self, db):
        db.raw_sql("CHECKPOINT")
        block_size, used_blocks = db.raw_sql(
            "select block_size, used_blocks from pragma_database_size() "
            "where database_name = current_database()"
        ).fetchone()
        return block_size * used_blocks

    # @feature data-store.storage-measure
    def test_column_bytes_sum_to_what_dropping_the_table_frees(self):
        with self.warehouse_file() as (db, _):
            self.create_wide_table(db, "s", "wide")
            db.raw_sql('create table "s".other as select i from range(10) t(i)')
            db.raw_sql("CHECKPOINT")

            measured = measure_table(db, "s", "wide")
            used_before = self.used_bytes(db)
            db.raw_sql('drop table "s".wide')
            freed = used_before - self.used_bytes(db)

        self.assertEqual(measured["rows"], 2000)
        self.assertEqual(sum(measured["columns"].values()), measured["bytes"])
        self.assertEqual(measured["bytes"], freed)
        self.assertEqual(set(measured["columns"]), {"i", "body", "bucket"})
        self.assertGreater(measured["columns"]["i"], 0, "a column sharing a block gets a share of it")
        self.assertGreater(measured["columns"]["body"], 10 * measured["columns"]["i"])

    # @feature data-store.storage-measure
    def test_measure_lists_every_table_and_counts_space_a_dropped_column_frees(self):
        with self.measured_warehouse() as db:
            self.create_wide_table(db, "a", "wide")
            db.raw_sql('create schema "b"')
            db.raw_sql('create table "b".small as select i from range(10) t(i)')

            first = measure_data_store()
            db.raw_sql('alter table "a".wide drop column body')
            second = measure_data_store()

            self.assertEqual(get_storage(), second)

        self.assertEqual(set(first["tables"]), {"a.wide", "b.small"})
        self.assertEqual(first["tables"]["b.small"]["rows"], 10)
        self.assertNotIn("body", second["tables"]["a.wide"]["columns"])
        # The column's share of the block it shares with others stays used.
        self.assertGreaterEqual(
            second["free_bytes"] - first["free_bytes"],
            first["tables"]["a.wide"]["columns"]["body"] - first["block_size"],
        )

    # @feature data-store.storage-measure
    def test_recording_one_table_keeps_the_other_entries(self):
        with self.measured_warehouse() as db:
            self.create_wide_table(db, "a", "wide")
            db.raw_sql('create schema "b"')
            db.raw_sql('create table "b".small as select i from range(10) t(i)')
            before = measure_data_store()

            db.raw_sql('insert into "b".small select i from range(10, 25) t(i)')
            record_table_storage(db, "b", "small")
            after = get_storage()

        self.assertEqual(after["tables"]["b.small"]["rows"], 25)
        self.assertEqual(after["tables"]["a.wide"], before["tables"]["a.wide"])
        self.assertEqual(after["measured_on"], before["measured_on"])
        self.assertEqual(after["free_bytes"], before["free_bytes"])
