# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint
from frappe.database.mariadb.database import MariaDBDatabase

from insights.insights.doctype.insights_data_source.connectors.model import (
    BaseDataSource,
)
from insights.insights.doctype.insights_data_source.common import (
    NotSelectQuery,
    connect_to_db,
    insights_table_exists,
)


class CustomMariaDB(MariaDBDatabase):
    def __init__(self, dbName, *args, useSSL=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.useSSL = useSSL
        self.dbName = dbName

    def get_connection_settings(self) -> dict:
        conn_settings = super().get_connection_settings()
        conn_settings["ssl"] = self.useSSL
        conn_settings["ssl_verify_cert"] = self.useSSL

        if self.user != "root":
            # Fix: cannot connect to non-frappe MariaDB instances where database name != user name
            conn_settings["database"] = self.dbName
        return conn_settings


class RemoteMariaDB(BaseDataSource):
    def test_connection(self):
        query = self.get_test_query()
        try:
            self.get_data(query)
            return True
        except Exception as e:
            frappe.log_error(f"Error connecting to RemoteDB: {e}")
            print("Error connecting to RemoteDB: {e}")

    def get_test_query(self):
        return "SELECT 1"

    def create_connection(self):
        return CustomMariaDB(
            host=self.doc.host,
            port=cint(self.doc.port),
            user=self.doc.username,
            password=self.doc.get_password(),
            useSSL=self.doc.use_ssl,
            dbName=self.doc.database_name,
        )

    def get_data(self, query, *args, **kwargs):
        self.validate_query(query)
        result = []
        try:
            with connect_to_db(self.get_connection()) as db:
                result = db.sql(query, *args, **kwargs)
        except Exception as e:
            frappe.log_error(f"Error fetching data from RemoteDB: {e}")
            raise
        return result

    def validate_query(self, query):
        """Check if SQL query is safe for running in restricted context.

        Safe queries:
                1. Read only 'select' or 'explain' queries
                2. CTE on mariadb where writes are not allowed.
        """

        if not query:
            frappe.throw("Query cannot be empty")

        if self.flags.get("skip_validation"):
            self.flags.skip_validation = False
            return

        query = query.strip().lower()
        whitelisted_statements = ("select", "explain")

        if query.startswith(whitelisted_statements) or (
            query.startswith("with") and frappe.db.db_type == "mariadb"
        ):
            return True

        frappe.throw(
            "Query must be of SELECT or read-only WITH type.",
            title="Unsafe SQL query",
            exc=NotSelectQuery,
        )

    def get_insights_tables(self):
        """Returns a list of tables with columns and links that can be used for insights"""
        tables = self.get_table_list()
        for table in tables:
            table.columns = self.get_columns(table.name)
            table.links = self.get_links(table.name)
        return tables

    def get_table_list(self):
        query = """
            SELECT table_name as name, table_name as label
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        """
        tables = self.get_data(query, as_dict=True)
        tables = self.process_tables(tables) if self.process_tables else tables
        return tables

    def get_columns(self, table):
        query = """
            select column_name as name, data_type as type
            from information_schema.columns
            where table_name = %s
        """
        # TODO: caching
        columns = self.get_data(query, values=table, as_dict=1)
        columns = self.process_columns(columns) if self.process_columns else columns
        return columns

    def process_columns(self, columns):
        # TODO: extract into FrappeDB connector
        _columns = [
            {
                "column": d.name,
                "type": convert_to_insights_column_type(d.type),
                "label": frappe.unscrub(d.name).rstrip().lstrip(),
            }
            for d in columns
        ]
        return _columns

    def get_links(self, table):
        """Returns a list of links in the table"""
        query = """
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
        """
        links = self.get_data(query, values=table, as_dict=True)
        links = self.process_links(links) if self.process_links else links
        return links

    def process_links(self, links):
        _links = []
        for link in links:
            _links.append(
                {
                    "primary_key": link.column_name,
                    "foreign_key": link.foreign_column_name,
                    "foreign_table": link.foreign_table_name,
                    "foreign_table_label": frappe.unscrub(link.foreign_table_name)
                    .rstrip()
                    .lstrip(),
                }
            )

    def create_insights_tables(self, force=False):
        for table in self.get_insights_tables():
            if docname := insights_table_exists(self.doc.name, table.name):
                doc = frappe.get_doc("Insights Table", docname)
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "Insights Table",
                        "data_source": self.doc.name,
                        "table": table.name,
                        "label": table.label,
                    }
                )

            doc.label = table.label
            if force:
                doc.table_links = []
                doc.columns = []

            for table_link in table.links:
                if not doc.get("table_links", table_link):
                    doc.append("table_links", table_link)

            for column in table.columns:
                if not doc.get("columns", column):
                    doc.append("columns", column)

            doc.save()

    def get_running_jobs(self):
        query = """
            select
                id, user, db, command, time, state, info, progress
            from
                information_schema.processlist
            where
                user = %s
                and db = %s
                and info not like '%information_schema.processlist%'
            """
        self.flags.skip_validation = True
        return self.get_data(
            query, values=(self.doc.username, self.doc.database_name), as_dict=True
        )

    def kill_running_job(self, job_id):
        self.flags.skip_validation = True
        self.get_data(f"kill {job_id}")

    def get_distinct_column_values(
        self, table, column, search_text=None, limit=25
    ) -> "list[str]":
        Table = frappe.qb.Table(table)
        Column = frappe.qb.Field(column)
        query = frappe.qb.from_(Table).select(Column).distinct().limit(limit)
        if search_text:
            query = query.where(Column.like(f"%{search_text}%"))
        values = self.get_data(query.get_sql(), pluck=True)
        # TODO: cache
        return values

    def describe_table(self, table, limit=20):
        self.flags.skip_validation = True
        columns = self.get_data(f"""desc `{table}`""")
        data = self.get_data(f"""select * from `{table}` limit {limit}""")
        no_of_rows = self.get_data(f"""select count(*) from `{table}`""")[0][0]
        return columns, data, no_of_rows


class RemoteFrappeDB(RemoteMariaDB):
    def process_tables(self, tables):
        _tables = []
        for table in tables:
            if "__" in table.name:
                continue
            table.label = self.get_table_label(table.name)
            _tables.append(table)
        return _tables

    def get_table_label(self, table):
        return table.replace("tab", "")

    def get_links(self, table):
        if not hasattr(self, "_all_links") or not self._all_links:
            self._all_links = self.get_all_links()
        return self._all_links.get(table, [])

    def get_all_links(self):
        table_links_map = {}

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
        standard_links = self.get_data(query, as_dict=1)

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
        custom_links = self.get_data(query, as_dict=1)

        for link in standard_links + custom_links:
            if link.get("fieldtype") == "Link":
                # User is linked with ToDo by `owner` field
                # User.name = ToDo.owner
                table_links_map.setdefault(link.get("options"), []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )
                # ToDo is linked with User by `owner` field
                # ToDo.owner = User.name
                table_links_map.setdefault(link.get("parent"), []).append(
                    {
                        "primary_key": link.get("fieldname"),
                        "foreign_key": "name",
                        "foreign_table": "tab" + link.get("options"),
                        "foreign_table_label": link.get("options"),
                    }
                )
            if link.get("fieldtype") == "Table":
                table_links_map.setdefault(link.get("parent"), []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": "parent",
                        "foreign_table": "tab" + link.get("options"),
                        "foreign_table_label": link.get("options"),
                    }
                )
                table_links_map.setdefault(link.get("options"), []).append(
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
                table_links_map.setdefault(doctype, []).append(
                    {
                        "primary_key": "name",
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )
                table_links_map.setdefault(link.get("parent"), []).append(
                    {
                        "primary_key": link.get("fieldname"),
                        "foreign_key": "name",
                        "foreign_table": "tab" + doctype,
                        "foreign_table_label": doctype,
                    }
                )

        return table_links_map

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
            dynamic_links += self.get_data(query, as_dict=True)

        for df in dynamic_links:
            if df.issingle:
                dynamic_link_map.setdefault(df.parent, []).append(df)
            else:
                try:
                    links = self.get_data(
                        """select distinct {options} from `tab{parent}`""".format(**df)
                    )
                    links = [l[0] for l in links]
                    for doctype in links:
                        dynamic_link_map.setdefault(doctype, []).append(df)
                except frappe.db.TableMissingError:  # noqa: E722
                    pass

        return dynamic_link_map


def convert_to_insights_column_type(data_type):
    COLUMN_TYPE_MAP = {
        "time": "Time",
        "date": "Date",
        "varchar": "String",
        "int": "Integer",
        "float": "Decimal",
        "datetime": "Datetime",
        "text": "Text",
        "longtext": "Text",
        "enum": "String",
        "decimal": "Decimal",
        "bigint": "Integer",
        "timestamp": "Datetime",
    }
    return COLUMN_TYPE_MAP.get(data_type.lower(), "String")
