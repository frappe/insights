# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _dict
from sqlalchemy import column as Column
from sqlalchemy import table as Table
from sqlalchemy import text
from sqlalchemy.engine.base import Connection

from insights.insights.query_builders.sql_builder import SQLQueryBuilder

from .base_database import (
    BaseDatabase,
    DatabaseCredentialsError,
    DatabaseParallelConnectionError,
)
from .mariadb import MARIADB_TO_GENERIC_TYPES, MariaDB
from .utils import create_insights_table, get_sqlalchemy_engine


class FrappeTableFactory:
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
            table.table_links = self.get_table_links(table.label)
            create_insights_table(table, force=force)

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
            if not table_name.startswith("tab"):
                continue
            schema.setdefault(table_name, []).append(self.get_column(column_name, data_type))
        return schema

    def get_table(self, table_name):
        return _dict(
            {
                "table": table_name,
                "label": table_name.replace("tab", "").title(),
                "data_source": self.data_source,
            }
        )

    def get_column(self, column_name, column_type):
        return _dict(
            {
                "column": column_name,
                "label": frappe.unscrub(column_name),
                "type": MARIADB_TO_GENERIC_TYPES.get(column_type, "String"),
            }
        )

    def get_table_links(self, doctype):
        if not hasattr(self, "_all_links") or not self._all_links:
            self._all_links = self.get_all_links()
        return self._all_links.get(doctype, [])

    def get_all_links(self):
        doctype_links = {}

        DocField = frappe.qb.DocType("DocField")
        query = (
            frappe.qb.from_(DocField)
            .select(
                DocField.fieldname,
                DocField.fieldtype,
                DocField.options,
                DocField.parent,
            )
            .where((DocField.fieldtype == "Link") | (DocField.fieldtype == "Table"))
            .get_sql()
        )
        query = text(query)
        standard_links = self.db_conn.execute(query).fetchall()

        CustomField = frappe.qb.DocType("Custom Field")
        query = (
            frappe.qb.from_(CustomField)
            .select(
                CustomField.fieldname,
                CustomField.fieldtype,
                CustomField.options,
                CustomField.dt.as_("parent"),
            )
            .where((CustomField.fieldtype == "Link") | (CustomField.fieldtype == "Table"))
            .get_sql()
        )
        query = text(query)
        custom_links = self.db_conn.execute(query).fetchall()

        for link_row in standard_links + custom_links:
            link = _dict(link_row._asdict())
            if link.fieldtype == "Link":
                # User is linked with ToDo by `owner` field
                # User.name = ToDo.owner
                doctype_links.setdefault(link.options, []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": link.fieldname,
                        "foreign_table": "tab" + link.parent,
                        "foreign_table_label": link.parent,
                        "cardinality": "1:N",
                    }
                )
            if link.fieldtype == "Table":
                doctype_links.setdefault(link.parent, []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": "parent",
                        "foreign_table": "tab" + link.options,
                        "foreign_table_label": link.options,
                        "cardinality": "1:N",
                    }
                )

        return doctype_links

    def get_dynamic_link_map(self):
        # copied from frappe.model.dynamic_links

        DocField = frappe.qb.DocType("DocField")
        DocType = frappe.qb.DocType("DocType")
        CustomField = frappe.qb.DocType("Custom Field")

        standard_dynamic_links_query = (
            frappe.qb.from_(DocField)
            .from_(DocType)
            .select(
                DocField.parent,
                DocField.fieldname,
                DocField.options,
                DocType.issingle,
            )
            .where((DocField.fieldtype == "Dynamic Link") & (DocType.name == DocField.parent))
            .get_sql()
        )

        custom_dynamic_links_query = (
            frappe.qb.from_(CustomField)
            .from_(DocType)
            .select(
                CustomField.dt.as_("parent"),
                CustomField.fieldname,
                CustomField.options,
                DocType.issingle,
            )
            .where((CustomField.fieldtype == "Dynamic Link") & (DocType.name == CustomField.dt))
            .get_sql()
        )

        dynamic_link_queries = [
            text(standard_dynamic_links_query),
            text(custom_dynamic_links_query),
        ]

        dynamic_link_map = {}
        dynamic_links = []
        for query in dynamic_link_queries:
            dynamic_links += self.db_conn.execute(query).fetchall()

        for df_row in dynamic_links:
            df = _dict(df_row._asdict())
            if df.issingle:
                dynamic_link_map.setdefault(df.parent, []).append(df)
            else:
                try:
                    links = self.db_conn.execute(
                        text(f"""select distinct {df.options} from `tab{df.parent}`""")
                    ).fetchall()
                except Exception:
                    continue
                links = [l[0] for l in links]
                for doctype in links:
                    dynamic_link_map.setdefault(doctype, []).append(df)

        return dynamic_link_map


class FrappeDB(MariaDB):
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
            ssl_verify_cert=True,
            charset="utf8mb4",
            use_unicode=True,
            connect_args={"connect_timeout": 1, "read_timeout": 1, "write_timeout": 1},
        )
        self.query_builder: SQLQueryBuilder = SQLQueryBuilder(self.engine)
        self.table_factory: FrappeTableFactory = FrappeTableFactory(data_source)

    def test_connection(self, log_errors=True):
        return self.execute_query(
            "select name from tabDocType limit 1", pluck=True, log_errors=log_errors
        )

    def handle_db_connection_error(self, e):
        if "Access denied" in str(e):
            raise DatabaseCredentialsError()
        if "Packet sequence number wrong" in str(e):
            raise DatabaseParallelConnectionError()
        super().handle_db_connection_error(e)

    def sync_tables(self, tables=None, force=False):
        # "begin" ensures that the connection is committed and closed
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
        t = Table(table, Column(column))
        query = t.select().distinct().limit(limit)
        if search_text:
            query = query.where(Column(column).like(f"%{search_text}%"))
        query = self.compile_query(query)
        return self.execute_query(query, pluck=True)


class SiteDB(FrappeDB):
    def __init__(self, data_source):
        self.data_source = data_source
        self.engine = get_sqlalchemy_engine(
            dialect="mysql",
            driver="pymysql",
            username=frappe.conf.db_name,
            password=frappe.conf.db_password,
            database=frappe.conf.db_name,
            host=frappe.conf.db_host or "127.0.0.1",
            port=frappe.conf.db_port or "3306",
            ssl=False,
            ssl_verify_cert=True,
            charset="utf8mb4",
            use_unicode=True,
        )
        self.query_builder: SQLQueryBuilder = SQLQueryBuilder(self.engine)
        self.table_factory: FrappeTableFactory = FrappeTableFactory(data_source)


from insights.cache_utils import get_or_set_cache, make_digest


def is_frappe_db(db_params):
    def _is_frappe_db():
        try:
            FrappeDB(**db_params).test_connection(log_errors=False)
        except Exception:
            return False
        return True

    key = make_digest("is_frappe_db", db_params)
    return get_or_set_cache(key, _is_frappe_db, expiry=None)
