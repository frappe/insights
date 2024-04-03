# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from sqlalchemy import column as Column
from sqlalchemy import select as Select
from sqlalchemy import table as Table
from sqlalchemy import text
from sqlalchemy.engine.base import Connection
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from insights.insights.query_builders.sql_builder import SQLQueryBuilder

from .base_database import (
    BaseDatabase,
    DatabaseCredentialsError,
    DatabaseParallelConnectionError,
)
from .utils import create_insights_table, get_sqlalchemy_engine

MARIADB_TO_GENERIC_TYPES = {
    "int": "Integer",
    "bigint": "Long Int",
    "decimal": "Decimal",
    "text": "Text",
    "longtext": "Long Text",
    "date": "Date",
    "datetime": "Datetime",
    "time": "Time",
    "varchar": "String",
}


class MariaDBTableFactory:
    """Fetchs tables and columns from database and links from doctype"""

    def __init__(self, data_source) -> None:
        self.db_conn: Connection
        self.data_source = data_source

    def sync_tables(self, connection, tablenames, force=False):
        self.db_conn = connection
        self.columns_by_tables = self.get_columns_by_tables(tablenames)
        for tablename, columns in self.columns_by_tables.items():
            table = self.get_table(tablename)
            table.columns = columns
            # infer table links from foreign key constraints
            # table.table_links = self.get_table_links(table.label)
            create_insights_table(table, force=force)

    def get_table(self, table_name):
        return frappe._dict(
            {
                "table": table_name,
                "label": frappe.unscrub(table_name),
                "data_source": self.data_source,
            }
        )

    def get_columns_by_tables(self, tablenames=None):
        t = Table(
            "columns",
            Column("table_name"),
            Column("column_name"),
            Column("data_type"),
            Column("table_schema"),
            schema="information_schema",
        )

        query = t.select().where(t.c.table_schema == text("DATABASE()"))
        if tablenames:
            query = query.where(t.c.table_name.in_(tablenames))

        columns = self.db_conn.execute(query).fetchall()

        schema = {}
        for [table_name, column_name, data_type, _] in columns:
            schema.setdefault(table_name, []).append(self.get_column(column_name, data_type))
        return schema

    def get_column(self, column_name, column_type):
        return frappe._dict(
            {
                "column": column_name,
                "label": frappe.unscrub(column_name),
                "type": MARIADB_TO_GENERIC_TYPES.get(column_type, "String"),
            }
        )


class MariaDB(BaseDatabase):
    def __init__(self, data_source, host, port, username, password, database_name, use_ssl, **_):
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
            connect_args={"connect_timeout": 1},
        )
        self.query_builder: SQLQueryBuilder = SQLQueryBuilder(self.engine)
        self.table_factory: MariaDBTableFactory = MariaDBTableFactory(data_source)

    @retry(
        retry=retry_if_exception_type((DatabaseParallelConnectionError,)),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
    )
    def connect(self, *args, **kwargs):
        return super().connect(*args, **kwargs)

    def handle_db_connection_error(self, e):
        if "Access denied" in str(e):
            raise DatabaseCredentialsError()
        if "Packet sequence number wrong" in str(e):
            raise DatabaseParallelConnectionError()
        super().handle_db_connection_error(e)

    def sync_tables(self, tables=None, force=False):
        with self.engine.begin() as connection:
            self.table_factory.sync_tables(connection, tables, force)

    def get_table_preview(self, table, limit=100):
        data = self.execute_query(f"""select * from `{table}` limit {limit}""", cached=True)
        length = self.execute_query(f"""select count(*) from `{table}`""", cached=True)[0][0]
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
