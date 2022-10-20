# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe

from frappe.utils import cint
from .models import BaseDataSource
from frappe.database.mariadb.database import MariaDBDatabase
from .utils import SecureMariaDB, create_insights_table, MARIADB_TO_GENERIC_TYPES
from insights.insights.query_builders.frappe_qb import FrappeQueryBuilder


class FrappeTableFactory:
    """Fetchs tables and columns from database and links from doctype"""

    def __init__(self, data_source, db_conn) -> None:
        self.db_conn: SecureMariaDB = db_conn
        self.data_source = data_source

    def get_tables(self, table_names=None):
        tables = []
        for table in self.get_db_tables(table_names):
            table.columns = self.get_table_columns(table.table)
            table.table_links = self.get_table_links(table.label)
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
                "label": table_name.replace("tab", ""),
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
        standard_links = self.db_conn.sql(query, as_dict=1)

        CustomField = frappe.qb.DocType("Custom Field")
        query = (
            frappe.qb.from_(CustomField)
            .select(
                CustomField.fieldname,
                CustomField.fieldtype,
                CustomField.options,
                CustomField.dt.as_("parent"),
            )
            .where(
                (CustomField.fieldtype == "Link") | (CustomField.fieldtype == "Table")
            )
            .get_sql()
        )
        custom_links = self.db_conn.sql(query, as_dict=1)

        for link in standard_links + custom_links:
            if link.get("fieldtype") == "Link":
                # User is linked with ToDo by `owner` field
                # User.name = ToDo.owner
                doctype_links.setdefault(link.get("options"), []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )
                # ToDo is linked with User by `owner` field
                # ToDo.owner = User.name
                doctype_links.setdefault(link.get("parent"), []).append(
                    {
                        "primary_key": link.get("fieldname"),
                        "foreign_key": "name",
                        "foreign_table": "tab" + link.get("options"),
                        "foreign_table_label": link.get("options"),
                    }
                )
            if link.get("fieldtype") == "Table":
                doctype_links.setdefault(link.get("parent"), []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": "parent",
                        "foreign_table": "tab" + link.get("options"),
                        "foreign_table_label": link.get("options"),
                    }
                )
                doctype_links.setdefault(link.get("options"), []).append(
                    {
                        "primary_key": "parent",
                        "foreign_key": "name",
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
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
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )
                doctype_links.setdefault(link.get("parent"), []).append(
                    {
                        "primary_key": link.get("fieldname"),
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
            .where(
                (DocField.fieldtype == "Dynamic Link")
                & (DocType.name == DocField.parent)
            )
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
            .where(
                (CustomField.fieldtype == "Dynamic Link")
                & (DocType.name == CustomField.dt)
            )
            .get_sql()
        )

        dynamic_link_queries = [
            standard_dynamic_links_query,
            custom_dynamic_links_query,
        ]

        dynamic_link_map = {}
        dynamic_links = []
        for query in dynamic_link_queries:
            dynamic_links += self.db_conn.sql(query, as_dict=True)

        for df in dynamic_links:
            if df.issingle:
                dynamic_link_map.setdefault(df.parent, []).append(df)
            else:
                try:
                    links = self.db_conn.sql(
                        """select distinct {options} from `tab{parent}`""".format(**df)
                    )
                    links = [l[0] for l in links]
                    for doctype in links:
                        dynamic_link_map.setdefault(doctype, []).append(df)
                except frappe.db.TableMissingError:  # noqa: E722
                    pass

        return dynamic_link_map


class FrappeDB(BaseDataSource):
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
        self.query_builder: FrappeQueryBuilder = FrappeQueryBuilder()
        self.table_factory: FrappeTableFactory = FrappeTableFactory(
            data_source, db_conn=self.conn
        )

    def test_connection(self):
        try:
            return self.conn.sql("select name from `tabDocType` limit 1")
        except Exception as e:
            frappe.log_error(f"Error connecting to Site: {e}")

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


class SiteDB(FrappeDB):
    def __init__(self, data_source):
        self.conn: MariaDBDatabase = MariaDBDatabase()
        self.query_builder: FrappeQueryBuilder = FrappeQueryBuilder()
        self.table_factory: FrappeTableFactory = FrappeTableFactory(
            data_source, db_conn=self.conn
        )

    def sync_tables(self, tables=None, force=False):
        # only import tables that are not related to insights
        _tables = tables or [
            table
            for table in frappe.db.get_tables()
            if not table.startswith("tabInsights")
        ]
        return super().sync_tables(_tables, force)


def is_frappe_db(db_params):
    try:
        return FrappeDB(**db_params).test_connection()
    except BaseException:
        print("Not a Frappe DB")
        return False
