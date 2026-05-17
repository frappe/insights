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

    def patched_write_connection(self, db):
        @contextmanager
        def get_write_connection(database=None, timeout=30):
            if database:
                db.raw_sql(f"USE '{database}'")
            yield db

        return get_write_connection

    def read_rows(self, db, table_name):
        rows = db.table(table_name).order_by("id").execute()
        rows["modified"] = rows["modified"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return rows.to_dict("records")

    def test_writer_creates_table_on_first_commit(self):
        with self.warehouse_db() as db:
            with patch.object(
                insights.warehouse,
                "get_write_connection",
                self.patched_write_connection(db),
            ):
                with WarehouseTableWriter(
                    "warehouse_writer_create",
                    table_schema=self.make_schema(),
                    database="main",
                    mode="replace",
                ) as writer:
                    writer.insert(
                        self.make_frame(
                            [
                                {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                                {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                            ]
                        )
                    )
                    rows_written = writer.commit()
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "warehouse_writer_create"),
                [
                    {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
            )

    def test_writer_append_mode_keeps_existing_rows(self):
        with self.warehouse_db() as db:
            with patch.object(
                insights.warehouse,
                "get_write_connection",
                self.patched_write_connection(db),
            ):
                with WarehouseTableWriter(
                    "warehouse_writer_append",
                    table_schema=self.make_schema(),
                    database="main",
                    mode="replace",
                ) as writer:
                    writer.insert(
                        self.make_frame([{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}])
                    )
                    writer.commit()

                with WarehouseTableWriter(
                    "warehouse_writer_append",
                    table_schema=self.make_schema(),
                    database="main",
                    mode="append",
                ) as writer:
                    writer.insert(
                        self.make_frame(
                            [
                                {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                                {"id": 3, "value": "gamma", "modified": "2024-01-03 00:00:00"},
                            ]
                        )
                    )
                    rows_written = writer.commit()
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "warehouse_writer_append"),
                [
                    {"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                    {"id": 3, "value": "gamma", "modified": "2024-01-03 00:00:00"},
                ],
            )

    def test_writer_upsert_mode_updates_matching_primary_keys(self):
        with self.warehouse_db() as db:
            with patch.object(
                insights.warehouse,
                "get_write_connection",
                self.patched_write_connection(db),
            ):
                with WarehouseTableWriter(
                    "warehouse_writer_upsert",
                    table_schema=self.make_schema(),
                    database="main",
                    mode="replace",
                ) as writer:
                    writer.insert(
                        self.make_frame([{"id": 1, "value": "alpha", "modified": "2024-01-01 00:00:00"}])
                    )
                    writer.commit()

                with WarehouseTableWriter(
                    "warehouse_writer_upsert",
                    table_schema=self.make_schema(),
                    database="main",
                    mode="upsert",
                    primary_key_column="id",
                    cursor_column="modified",
                ) as writer:
                    writer.insert(
                        self.make_frame(
                            [
                                {"id": 1, "value": "updated", "modified": "2024-01-02 00:00:00"},
                                {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                            ]
                        )
                    )
                    rows_written = writer.commit()
            self.assertEqual(rows_written, 2)
            self.assertEqual(
                self.read_rows(db, "warehouse_writer_upsert"),
                [
                    {"id": 1, "value": "updated", "modified": "2024-01-02 00:00:00"},
                    {"id": 2, "value": "beta", "modified": "2024-01-02 00:00:00"},
                ],
            )
