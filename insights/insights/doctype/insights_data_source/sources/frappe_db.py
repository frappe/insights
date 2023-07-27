# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _dict
from sqlalchemy import column as Column
from sqlalchemy import table as Table
from sqlalchemy import text
from sqlalchemy.engine.base import Connection

from insights.insights.query_builders.sql_builder import SQLQueryBuilder

from .base_database import BaseDatabase
from .mariadb import MARIADB_TO_GENERIC_TYPES
from .utils import create_insights_table, get_sqlalchemy_engine


class FrappeTableFactory:
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
            table.table_links = self.get_table_links(table.label)
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
        return [self.get_table(table[0]) for table in tables if not table[0].startswith("__")]

    def get_table(self, table_name):
        return _dict(
            {
                "table": table_name,
                "label": table_name.replace("tab", ""),
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
            columns_by_table.setdefault(col[0], []).append(self.get_column(col[1], col[2]))
        return columns_by_table

    def get_table_columns(self, table):
        if not hasattr(self, "_all_columns") or not self._all_columns:
            self._all_columns = self.get_all_columns()
        return self._all_columns.get(table, [])

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
                    }
                )
                # ToDo is linked with User by `owner` field
                # ToDo.owner = User.name
                doctype_links.setdefault(link.parent, []).append(
                    {
                        "primary_key": link.fieldname,
                        "foreign_key": "name",
                        "foreign_table": "tab" + link.options,
                        "foreign_table_label": link.options,
                    }
                )
            if link.fieldtype == "Table":
                doctype_links.setdefault(link.parent, []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": "parent",
                        "foreign_table": "tab" + link.options,
                        "foreign_table_label": link.options,
                    }
                )
                doctype_links.setdefault(link.options, []).append(
                    {
                        "primary_key": "parent",
                        "foreign_key": "name",
                        "foreign_table": "tab" + link.parent,
                        "foreign_table_label": link.parent,
                    }
                )

        dynamic_links = self.get_dynamic_link_map()
        for doctype in dynamic_links:
            if not doctype:
                continue

            for link in dynamic_links.get(doctype):
                doctype_links.setdefault(doctype, []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": link.fieldname,
                        "foreign_table": "tab" + link.parent,
                        "foreign_table_label": link.parent,
                    }
                )
                doctype_links.setdefault(link.parent, []).append(
                    {
                        "primary_key": link.fieldname,
                        "foreign_key": "name",
                        "foreign_table": "tab" + doctype,
                        "foreign_table_label": doctype,
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
            standard_dynamic_links_query,
            custom_dynamic_links_query,
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
                links = self.db_conn.execute(
                    f"""select distinct {df.options} from `tab{df.parent}`"""
                ).fetchall()
                links = [l[0] for l in links]
                for doctype in links:
                    dynamic_link_map.setdefault(doctype, []).append(df)

        return dynamic_link_map


class FrappeDB(BaseDatabase):
    def __init__(self, data_source, host, port, username, password, database_name, use_ssl):
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
        )
        self.query_builder: SQLQueryBuilder = SQLQueryBuilder()
        self.table_factory: FrappeTableFactory = FrappeTableFactory(data_source)

    def test_connection(self):
        return self.execute_query("select name from `tabDocType` limit 1", pluck=True)

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
        self.query_builder: SQLQueryBuilder = SQLQueryBuilder()
        self.table_factory: FrappeTableFactory = FrappeTableFactory(data_source)


from insights.cache_utils import get_or_set_cache, make_digest


def is_frappe_db(db_params):
    def _is_frappe_db():
        try:
            db = FrappeDB(**db_params)
            return db.test_connection()
        except BaseException:
            return False

    key = make_digest("is_frappe_db", db_params)
    return get_or_set_cache(key, _is_frappe_db, expiry=None)
