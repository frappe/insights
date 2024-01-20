# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
from sqlalchemy import column as Column
from sqlalchemy import create_engine
from sqlalchemy import table as Table
from sqlalchemy import text
from sqlalchemy.engine.base import Connection

from insights.insights.query_builders.sqlite.sqlite_query_builder import (
    SQLiteQueryBuilder,
)
from insights.utils import detect_encoding

from ...insights_table_import.insights_table_import import InsightsTableImport
from .base_database import BaseDatabase
from .utils import create_insights_table


class SQLiteTableFactory:
    def __init__(self, data_source) -> None:
        self.db_conn: Connection
        self.data_source = data_source

    def sync_tables(self, connection, tables, force=False):
        self.db_conn = connection
        for table in self.get_tables(table_names=tables):
            # when force is true, it will overwrite the existing columns & links
            create_insights_table(table, force=force)

    def get_tables(self, table_names=None):
        tables = []
        for table in self.get_db_tables(table_names):
            table.columns = self.get_table_columns(table.table)
            tables.append(table)
        return tables

    def get_db_tables(self, table_names=None):
        t = Table(
            "sqlite_master",
            Column("name"),
            Column("type"),
        )
        query = t.select().where(t.c.type == "table")
        if table_names:
            query = query.where(t.c.name.in_(table_names))

        tables = self.db_conn.execute(query).fetchall()
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
        columns = self.db_conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
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
        database_path = frappe.get_site_path("private", "files", f"{database_name}.sqlite")
        self.engine = create_engine(f"sqlite:///{database_path}")
        self.data_source = data_source
        self.table_factory = SQLiteTableFactory(data_source)
        self.query_builder = SQLiteQueryBuilder(self.engine)

    def sync_tables(self, tables=None, force=False):
        with self.engine.begin() as connection:
            self.table_factory.sync_tables(connection, tables, force)

    def get_table_preview(self, table, limit=100):
        data = self.execute_query(f"""select * from `{table}` limit {limit}""")
        length = self.execute_query(f"""select count(*) from `{table}`""")[0][0]
        return {
            "data": data or [],
            "length": length or 0,
        }

    def get_table_columns(self, table):
        with self.connect() as connection:
            self.table_factory.db_conn = connection
            return self.table_factory.get_table_columns(table)

    def get_column_options(self, table, column, search_text=None, limit=50):
        t = Table(table, Column(column))
        query = t.select().distinct().limit(limit)
        if search_text:
            query = query.where(Column(column).like(f"%{search_text}%"))
        query = self.compile_query(query)
        return self.execute_query(query, pluck=True)

    def table_exists(self, table):
        return self.execute_query(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'",
        )

    def import_table(self, import_doc: InsightsTableImport):
        encoding = detect_encoding(import_doc._filepath)
        df = pd.read_csv(import_doc._filepath, encoding=encoding)

        df.columns = [frappe.scrub(c) for c in df.columns]
        columns_to_import = [c.column for c in import_doc.columns]

        df = df[columns_to_import]
        table = import_doc.table_name
        df.to_sql(
            name=table,
            con=self.engine,
            index=False,
            if_exists="replace",
        )
        create_insights_table(
            frappe._dict(
                {
                    "table": import_doc.table_name,
                    "label": import_doc.table_label,
                    "data_source": import_doc.data_source,
                    "columns": [
                        frappe._dict(
                            {
                                "column": column.column,
                                "label": column.label,
                                "type": column.type,
                            }
                        )
                        for column in import_doc.columns
                    ],
                }
            ),
            force=True,
        )
