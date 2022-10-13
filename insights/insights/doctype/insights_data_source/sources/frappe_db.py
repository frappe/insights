# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe

from .models import (
    Connection,
    QueryRunner,
    BaseDataSource,
    DataSourceImporter,
)
from .utils import FrappeSiteConnection, DatabaseQueryRunner
from insights.insights.query_builders.frappe_qb import FrappeQueryBuilder


class FrappeDataImporter(DataSourceImporter):
    def __init__(self, datasource, connection: Connection, query_runner: QueryRunner):
        self.datasource = datasource
        self.connection = connection
        self.query_runner = query_runner

    def import_data(self, force=False):
        for table in self.get_tables():
            if docname := insights_table_exists(self.datasource, table.name):
                doc = frappe.get_doc("Insights Table", docname)
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "Insights Table",
                        "data_source": self.datasource,
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

    def get_tables(self):
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
        tables = self.query_runner.execute(query, as_dict=True)
        tables = self.process_tables(tables)
        return tables

    def process_tables(self, tables):
        _tables = []
        for table in tables:
            if "__" in table.name:
                continue
            table.label = table.name.replace("tab", "")
            _tables.append(table)
        return _tables

    def get_columns(self, table):
        query = """
            select column_name as name, data_type as type
            from information_schema.columns
            where table_name = %s
        """
        # TODO: caching
        columns = self.query_runner.execute(query, values=table, as_dict=1)
        columns = self.process_columns(columns)
        return columns

    def process_columns(self, columns):
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
        standard_links = self.query_runner.execute(query, as_dict=1)

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
        custom_links = self.query_runner.execute(query, as_dict=1)

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
            dynamic_links += self.query_runner.execute(query, as_dict=True)

        for df in dynamic_links:
            if df.issingle:
                dynamic_link_map.setdefault(df.parent, []).append(df)
            else:
                try:
                    links = self.query_runner.execute(
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
        self.connection: FrappeSiteConnection = FrappeSiteConnection(
            host, port, username, password, database_name, use_ssl
        )
        self.query_builder: FrappeQueryBuilder = FrappeQueryBuilder()
        self.query_runner: DatabaseQueryRunner = DatabaseQueryRunner(self.connection)
        self.data_importer: FrappeDataImporter = FrappeDataImporter(
            data_source, self.connection, self.query_runner
        )

    def get_distinct_column_values(self, table, column, search_text=None, limit=25):
        Table = frappe.qb.Table(table)
        Column = frappe.qb.Field(column)
        query = frappe.qb.from_(Table).select(Column).distinct().limit(limit)
        if search_text:
            query = query.where(Column.like(f"%{search_text}%"))
        values = self.query_runner.execute(query.get_sql(), pluck=True)
        # TODO: cache
        return values

    def describe_table(self, table, limit=20):
        columns = self.query_runner.execute(f"""desc `{table}`""")
        data = self.query_runner.execute(f"""select * from `{table}` limit {limit}""")
        no_of_rows = self.query_runner.execute(f"""select count(*) from `{table}`""")[
            0
        ][0]
        return columns, data, no_of_rows


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


def insights_table_exists(datasource, tablename):
    return frappe.db.exists(
        "Insights Table", {"data_source": datasource, "table": tablename}
    )


def is_frappe_db(db_params):
    try:
        return FrappeDB(**db_params).connection.test()
    except BaseException:
        print("Not a Frappe DB")
        return False
