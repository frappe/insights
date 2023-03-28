# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from sqlalchemy import column as Column
from sqlalchemy import select as Select
from sqlalchemy import table as Table
from sqlalchemy import text
from sqlalchemy.engine.base import Connection

from insights.insights.query_builders.sql_builder import SQLQueryBuilder

from .base_database import BaseDatabase
from .utils import (
    MARIADB_TO_GENERIC_TYPES,
    create_insights_table,
    get_sqlalchemy_engine,
)


class MariaDBTableFactory:
    """Fetchs tables and columns from database and links from doctype"""

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
            # TODO: process foreign keys as links
            tables.append(table)
        return tables

    def get_db_tables(self, table_names=None):
        t = Table(
            "tables",
            Column("table_name"),
            Column("table_schema"),
            Column("table_type"),
            schema="information_schema",
        )

        query = (
            t.select()
            .where(t.c.table_schema == text("DATABASE()"))
            .where(t.c.table_type == "BASE TABLE")
        )
        if table_names:
            query = query.where(t.c.table_name.in_(table_names))

        tables = self.db_conn.execute(query).fetchall()
        return [
            self.get_table(table[0])
            for table in tables
            if not table[0].startswith("__")
        ]

    def get_table(self, table_name):
        return frappe._dict(
            {
                "table": table_name,
                "label": frappe.unscrub(table_name),
                "data_source": self.data_source,
            }
        )

    def get_all_columns(self):
        t = Table(
            "columns",
            Column("table_name"),
            Column("column_name"),
            Column("data_type"),
            Column("table_schema"),
            schema="information_schema",
        )

        query = t.select().where(t.c.table_schema == text("DATABASE()"))
        columns = self.db_conn.execute(query).fetchall()
        columns_by_table = {}
        for col in columns:
            columns_by_table.setdefault(col[0], []).append(
                self.get_column(col[1], col[2])
            )
        return columns_by_table

    def get_table_columns(self, table):
        if not hasattr(self, "_all_columns") or not self._all_columns:
            self._all_columns = self.get_all_columns()
        return self._all_columns.get(table, [])

    def get_column(self, column_name, column_type):
        return frappe._dict(
            {
                "column": column_name,
                "label": frappe.unscrub(column_name),
                "type": MARIADB_TO_GENERIC_TYPES.get(column_type, "String"),
            }
        )


class MariaDB(BaseDatabase):
    def __init__(
        self, data_source, host, port, username, password, database_name, use_ssl
    ):
        self.data_source = data_source
        self.engine = get_sqlalchemy_engine(
            dialect="mysql",
            driver="pymysql",
            username=username,
            password=password,
            database=database_name,
            host=host,
            port=port,
            ssl=use_ssl,
            ssl_verify_cert=use_ssl,
            charset="utf8mb4",
            use_unicode=True,
        )
        self.query_builder: SQLQueryBuilder = SQLQueryBuilder()
        self.table_factory: MariaDBTableFactory = MariaDBTableFactory(data_source)

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
        query = Select(Column(column)).select_from(Table(table)).distinct().limit(limit)
        if search_text:
            query = query.where(Column(column).like(f"%{search_text}%"))
        return self.execute_query(query, pluck=True, replace_query_tables=True)
