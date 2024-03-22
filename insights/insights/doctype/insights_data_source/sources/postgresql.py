# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re

import frappe
from sqlalchemy import column as Column
from sqlalchemy import inspect
from sqlalchemy import select as Select
from sqlalchemy import table as Table
from sqlalchemy import text
from sqlalchemy.engine.base import Connection

from insights.insights.query_builders.postgresql.builder import PostgresQueryBuilder

from .base_database import BaseDatabase
from .utils import create_insights_table, get_sqlalchemy_engine

IGNORED_TABLES = ["__.*"]

POSTGRESQL_TO_GENERIC_TYPES = {
    "integer": "Integer",
    "bigint": "Long Int",
    "numeric": "Decimal",
    "text": "Text",
    "varchar": "String",
    "date": "Date",
    "timestamp": "Datetime",
    "time": "Time",
    "longtext": "Long Text",
    "boolean": "String",  # TODO: change to boolean
}


class PostgresTableFactory:
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
        inspector = inspect(self.db_conn)
        tables = set(inspector.get_table_names()) | set(inspector.get_foreign_table_names())
        if table_names:
            tables = [table for table in tables if table in table_names]
        return [self.get_table(table) for table in tables if not self.should_ignore(table)]

    def should_ignore(self, table_name):
        return any(re.match(pattern, table_name) for pattern in IGNORED_TABLES)

    def get_table(self, table_name):
        return frappe._dict(
            {
                "table": table_name,
                "label": frappe.unscrub(table_name),
                "data_source": self.data_source,
            }
        )

    def get_all_columns(self):
        inspector = inspect(self.db_conn)
        tables = inspector.get_table_names()
        columns_by_table = {}
        for table in tables:
            columns = inspector.get_columns(table)
            for col in columns:
                columns_by_table.setdefault(table, []).append(
                    self.get_column(col["name"], col["type"])
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
                "type": POSTGRESQL_TO_GENERIC_TYPES.get(column_type, "String"),
            }
        )


class PostgresDatabase(BaseDatabase):
    def __init__(self, **kwargs):
        connect_args = {"connect_timeout": 1}

        self.data_source = kwargs.pop("data_source")
        if connection_string := kwargs.pop("connection_string", None):
            self.engine = get_sqlalchemy_engine(
                connection_string=connection_string, connect_args=connect_args
            )
        else:
            self.engine = get_sqlalchemy_engine(
                dialect="postgresql",
                driver="psycopg2",
                username=kwargs.pop("username"),
                password=kwargs.pop("password"),
                database=kwargs.pop("database_name"),
                host=kwargs.pop("host"),
                port=kwargs.pop("port"),
                sslmode="require" if kwargs.pop("use_ssl") else "disable",
                connect_args=connect_args,
            )
        self.query_builder: PostgresQueryBuilder = PostgresQueryBuilder(self.engine)
        self.table_factory: PostgresTableFactory = PostgresTableFactory(self.data_source)

    def sync_tables(self, tables=None, force=False):
        with self.engine.begin() as connection:
            self.table_factory.sync_tables(connection, tables, force)

    def get_table_preview(self, table, limit=100):
        data = self.execute_query(f"""select * from "{table}" limit {limit}""", cached=True)
        length = self.execute_query(f'''select count(*) from "{table}"''', cached=True)[0][0]
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
        query = self.compile_query(query)
        return self.execute_query(query, pluck=True)
