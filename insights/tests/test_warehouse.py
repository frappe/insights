import tempfile
from contextlib import contextmanager, suppress
from pathlib import Path
from unittest.mock import patch

import ibis
import pandas as pd

import insights
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import open_local_duckdb
from insights.insights.doctype.insights_data_source_v3.data_warehouse import WarehouseTableWriter
from insights.tests.base import InsightsIntegrationTestCase


class TestWarehouse(InsightsIntegrationTestCase):
    def make_schema(self):
        return ibis.schema({"id": "int64", "value": "string", "modified": "timestamp"})

    def make_frame(self, rows):
        frame = pd.DataFrame(rows)
        frame["modified"] = pd.to_datetime(frame["modified"])
        return frame

    @contextmanager
    def warehouse_db(self):
        with tempfile.TemporaryDirectory(prefix="insights_warehouse_test_") as tmpdir:
            db = open_local_duckdb(
                str(Path(tmpdir) / "warehouse.duckdb"),
                read_only=False,
                allowed_dir=str(Path(tempfile.gettempdir())),
            )
            try:
                yield db
            finally:
                with suppress(Exception):
                    db.disconnect()

    @contextmanager
    def patched_warehouse(self):
        with self.warehouse_db() as db:
            with patch.object(
                insights.warehouse,
                "get_write_connection",
                self._patched_write_connection(db),
            ):
                yield db

    def _patched_write_connection(self, db):
        @contextmanager
        def get_write_connection(database=None, timeout=30):
            if database:
                db.raw_sql(f"USE '{database}'")
            yield db

        return get_write_connection

    def write_to_table(self, db, table_name, rows, mode="replace", **kwargs):
        with WarehouseTableWriter(
            table_name,
            table_schema=self.make_schema(),
            database="main",
            mode=mode,
            **kwargs,
        ) as writer:
            writer.insert(self.make_frame(rows))
            return writer.commit()

    def read_rows(self, db, table_name):
        rows = db.table(table_name).order_by("id").execute()
        rows["modified"] = rows["modified"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return rows.to_dict("records")

    def test_writer_replace_mode(self):
        with self.patched_warehouse() as db:
            # First write — creates the table
            rows_written = self.write_to_table(
                db,
                "t",
                [
                    {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
            )
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "t"),
                [
                    {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
            )

            # Second write — table already exists; replace must overwrite, not silently drop data
            rows_written = self.write_to_table(
                db, "t", [{"id": 3, "value": "new", "modified": "2024-02-01 00:00:00"}]
            )
            self.assertEqual(rows_written, 1)
            self.assertEqual(
                self.read_rows(db, "t"),
                [{"id": 3, "value": "new", "modified": "2024-02-01 00:00:00"}],
            )

    def test_writer_append_mode_keeps_existing_rows(self):
        with self.patched_warehouse() as db:
            self.write_to_table(db, "t", [{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}])

            rows_written = self.write_to_table(
                db,
                "t",
                [
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                    {"id": 3, "value": "gamma", "modified": "2024-01-03 00:00:00"},
                ],
                mode="append",
            )
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "t"),
                [
                    {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                    {"id": 3, "value": "gamma", "modified": "2024-01-03 00:00:00"},
                ],
            )

    def test_writer_upsert_mode_updates_matching_primary_keys(self):
        with self.patched_warehouse() as db:
            self.write_to_table(db, "t", [{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}])

            rows_written = self.write_to_table(
                db,
                "t",
                [
                    {"id": 1, "value": "updated", "modified": "2024-01-02 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
                mode="upsert",
                primary_key_column="id",
                cursor_column="modified",
            )
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "t"),
                [
                    {"id": 1, "value": "updated", "modified": "2024-01-02 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
            )
