# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import sqlite3
import pandas as pd
from sqlite3 import Connection
from .models import BaseDatabase
from pypika import SQLLiteQuery, Table
from .utils import create_insights_table
from ...insights_table_import.insights_table_import import InsightsTableImport
from insights.insights.query_builders.sqlite.sqlite_query_builder import (
    SQLiteQueryBuilder,
)


class SQLiteTableFactory:
    def __init__(self, data_source, db_conn) -> None:
        self.db_conn: Connection = db_conn
        self.data_source = data_source

    def get_tables(self, table_names=None):
        tables = []
        for table in self.get_db_tables(table_names):
            table.columns = self.get_table_columns(table.table)
            tables.append(table)
        return tables

    def get_db_tables(self, table_names=None):
        table = Table("sqlite_master")
        query = (
            SQLLiteQuery.from_(table).select(table.name).where(table.type == "table")
        )
        if table_names:
            query = query.where(table.name.isin(table_names))

        tables = self.db_conn.execute(query.get_sql()).fetchall()
        return [self.get_table(table[0]) for table in tables]

    def get_table(self, table_name):
        return frappe._dict(
            {
                "table": table_name,
                "label": frappe.unscrub(table_name),
                "data_source": self.data_source,
            }
        )

    def get_table_columns(self, table_name):
        columns = self.db_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [
            frappe._dict(
                {
                    "column": column[1],
                    "label": frappe.unscrub(column[1]),
                    "type": self.get_column_type(column[2]),
                }
            )
            for column in columns
        ]

    def get_column_type(self, column_type):
        TYPE_MAP = {
            "NULL": "Integer",
            "INTEGER": "Integer",
            "REAL": "Decimal",
            "TEXT": "String",
            "BLOB": "String",
        }
        return TYPE_MAP.get(column_type, "String")


class SQLiteDB(BaseDatabase):
    def __init__(self, data_source, database_name) -> None:
        self.data_source = data_source
        self.conn = sqlite3.connect(
            frappe.get_site_path("private", "files", f"{database_name}.sqlite")
        )
        self.table_factory = SQLiteTableFactory(data_source, self.conn)
        self.query_builder = SQLiteQueryBuilder()

    def test_connection(self):
        try:
            return self.conn.execute("SELECT 1").fetchone()
        except Exception as e:
            frappe.log_error(f"Error connecting to MariaDB: {e}")

    def build_query(self, query):
        return self.query_builder.build(query)

    def execute_query(self, query, *args, **kwargs):
        return self.conn.execute(query, *args, **kwargs).fetchall()

    def sync_tables(self, tables=None, force=False):
        for table in self.table_factory.get_tables(table_names=tables):
            create_insights_table(table, force=force)

    def get_table_preview(self, table, limit=20):
        data = self.execute_query(
            SQLLiteQuery.from_(table).select("*").limit(limit).get_sql()
        )
        count = self.execute_query("SELECT COUNT(*) FROM %s" % table)[0][0]
        return {
            "data": data or [],
            "length": count or 0,
        }

    def table_exists(self, table):
        return self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )

    def import_table(self, import_doc: InsightsTableImport):
        if import_doc.if_exists == "Overwrite":
            self.conn.execute(f"DROP TABLE IF EXISTS {import_doc.table_name}")

        df = pd.read_csv(import_doc._filepath)
        df.to_sql(import_doc.table_name, self.conn, index=False)

        self.sync_tables(tables=[import_doc.table_name])
        # need to commit to release the lock
        self.conn.commit()
