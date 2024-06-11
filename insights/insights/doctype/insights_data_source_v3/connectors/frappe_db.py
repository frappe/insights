# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import ibis
from frappe import _dict
from sqlalchemy import column as Column
from sqlalchemy import table as Table
from sqlalchemy import text
from sqlalchemy.engine.base import Connection


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
            # create_insights_table(table, force=force)

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
            schema.setdefault(table_name, []).append(
                self.get_column(column_name, data_type)
            )
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
                "type": {}.get(column_type, "String"),
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
            .where(
                (CustomField.fieldtype == "Link") | (CustomField.fieldtype == "Table")
            )
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


def get_frappedb_connection_string(data_source):
    password = data_source.get_password(raise_exception=False)
    connection_string = (
        f"mysql://{data_source.username}:{password}"
        f"@{data_source.host}:{data_source.port}/{data_source.database_name}"
    )
    extra_args = frappe._dict(
        ssl=data_source.use_ssl,
        ssl_verify_cert=data_source.use_ssl,
        charset="utf8mb4",
        use_unicode=True,
    )
    return connection_string, extra_args


def get_sitedb_connection_string():
    username = frappe.conf.db_name
    password = frappe.conf.db_password
    database = frappe.conf.db_name
    host = frappe.conf.db_host or "127.0.0.1"
    port = frappe.conf.db_port or "3306"
    connection_string = f"mysql://{username}:{password}@{host}:{port}/{database}"
    extra_args = frappe._dict(
        ssl=False,
        ssl_verify_cert=False,
        charset="utf8mb4",
        use_unicode=True,
    )
    return connection_string, extra_args


def is_frappe_db(data_source):
    connection_string, extra_args = get_frappedb_connection_string(data_source)
    try:
        db = ibis.connect(connection_string, **extra_args)
        db.raw_sql("SET SESSION time_zone='+00:00'")
        db.raw_sql("SET collation_connection = 'utf8mb4_unicode_ci'")
        res = db.raw_sql("SELECT name FROM tabDocType LIMIT 1").fetchall()
        db.con.close()
        return len(res) > 0
    except Exception:
        return False
