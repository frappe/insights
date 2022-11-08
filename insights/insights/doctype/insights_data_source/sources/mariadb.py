# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe

from frappe.utils import cint
from .models import BaseDatabase
from .utils import SecureMariaDB, create_insights_table, MARIADB_TO_GENERIC_TYPES
from insights.insights.query_builders.mariadb.mariadb_query_builder import (
    MariaDBQueryBuilder,
)


class MariaDBTableFactory:
    """Fetchs tables and columns from database and links from doctype"""

    def __init__(self, data_source, db_conn) -> None:
        self.db_conn: SecureMariaDB = db_conn
        self.data_source = data_source

    def get_tables(self, table_names=None):
        tables = []
        for table in self.get_db_tables(table_names):
            table.columns = self.get_table_columns(table.table)
            # TODO: process foreign keys as links
            tables.append(table)
        return tables

    def get_db_tables(self, table_names=None):
        table = frappe.qb.Schema("information_schema").tables
        database_name = self.db_conn.sql("SELECT DATABASE()")[0][0]

        query = (
            frappe.qb.from_(table)
            .select(table.table_name)
            .where(
                (table.table_schema == database_name)
                and (table.table_type == "BASE TABLE")
            )
        )
        if table_names:
            query = query.where(table.table_name.isin(table_names))

        tables = self.db_conn.sql(query.get_sql(), pluck=True)
        return [self.get_table(table) for table in tables if not table.startswith("__")]

    def get_table(self, table_name):
        return frappe._dict(
            {
                "table": table_name,
                "label": frappe.unscrub(table_name),
                "data_source": self.data_source,
            }
        )

    def get_all_columns(self):
        columns = frappe.qb.Schema("information_schema").columns
        database_name = self.db_conn.sql("SELECT DATABASE()")[0][0]

        query = (
            frappe.qb.from_(columns)
            .select(
                columns.table_name,
                columns.column_name.as_("name"),
                columns.data_type.as_("type"),
            )
            .where(columns.table_schema == database_name)
        )

        columns = self.db_conn.sql(query.get_sql(), as_dict=True)
        columns_by_table = {}
        for c in columns:
            columns_by_table.setdefault(c.table_name, []).append(
                self.get_column(c.name, c.type)
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
        self.conn: SecureMariaDB = SecureMariaDB(
            dbName=database_name,
            user=username,
            password=password,
            host=host,
            port=cint(port),
            useSSL=use_ssl,
        )
        self.query_builder: MariaDBQueryBuilder = MariaDBQueryBuilder()
        self.table_factory: MariaDBTableFactory = MariaDBTableFactory(
            data_source, db_conn=self.conn
        )

    def test_connection(self):
        try:
            return self.conn.sql("select 1")
        except Exception as e:
            frappe.log_error(f"Error connecting to MariaDB: {e}")

    def build_query(self, query):
        return self.query_builder.build(query)

    def execute_query(self, query, *args, **kwargs):
        return self.conn.sql(query, *args, **kwargs)

    def sync_tables(self, tables=None, force=False):
        for table in self.table_factory.get_tables(table_names=tables):
            # when force is true, it will overwrite the existing columns & links
            create_insights_table(table, force=force)

    def get_table_preview(self, table, limit=20):
        data = self.execute_query(f"""select * from `{table}` limit {limit}""")
        length = self.execute_query(f"""select count(*) from `{table}`""")[0][0]
        return {
            "data": data or [],
            "length": length or 0,
        }

    def get_table_columns(self, table):
        return self.table_factory.get_table_columns(table)

    def get_column_options(self, table, column, search_text=None, limit=25):
        Table = frappe.qb.Table(table)
        Column = frappe.qb.Field(column)
        query = frappe.qb.from_(Table).select(Column).distinct().limit(limit)
        if search_text:
            query = query.where(Column.like(f"%{search_text}%"))
        values = self.execute_query(query.get_sql(), pluck=True)
        # TODO: cache
        return values
