# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.database.mariadb.database import MariaDBDatabase
from frappe.utils import cint
from frappe.model.document import Document

from contextlib import contextmanager


# exception class for when query is not a select query
class NotSelectQuery(frappe.ValidationError):
    pass


class DataSource(Document):
    def before_save(self):
        if self.test_connection():
            self.status = "Active"
        else:
            self.status = "Inactive"

    def on_update(self):
        self.import_tables()

    def on_trash(self):
        # TODO: optimize this
        linked_doctypes = ["Table"]
        for doctype in linked_doctypes:
            for table in frappe.db.get_all(doctype, {"data_source": self.name}):
                frappe.delete_doc(doctype, table.name)

    def create_db(self):
        if self.database_type != "MariaDB":
            raise NotImplementedError

        if self.database_type == "MariaDB":
            return MariaDBDatabase(
                host=self.host,
                port=cint(self.port),
                user=self.username,
                password=self.get_password(),
            )

    def get_db_instance(self):
        if not self.get("db_instance"):
            self.db_instance = self.create_db()

        # TODO: cache into site cache with key as self.name

        return self.db_instance

    def validate_query(self, query):
        """Check if SQL query is safe for running in restricted context.

        Safe queries:
                1. Read only 'select' or 'explain' queries
                2. CTE on mariadb where writes are not allowed.
        """

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

    def execute_query(self, query, **kwargs):
        if not query:
            return

        skip_validation = kwargs.pop("skip_validation", False)
        if not skip_validation:
            self.validate_query(query)

        result = []
        db_instance = self.get_db_instance()
        with connect_to_db(db_instance) as db:
            result = db.sql(query, **kwargs)

        return result

    @frappe.whitelist()
    def test_connection(self):
        connection_status = False

        try:
            self.execute_query("select 1")
            connection_status = True
        except Exception as e:
            frappe.log_error(title="Data Source Connection Test", message=e)

        return connection_status

    def check_if_frappe_db(self):
        # check if table `tabDoctype` exists in the database
        return self.execute_query("show tables like 'tabDoctype'", skip_validation=True)

    def get_tables(self, tables=None):
        if not tables:
            tables = []

        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        """
        tables = self.execute_query(query)
        tables = {d[0] for d in tables}

        # TODO: caching
        _tables = [
            {
                "table": table,
                "label": table.replace("tab", ""),
            }
            for table in list(tables)
        ]
        return _tables

    @frappe.whitelist()
    def import_tables(self):
        tables = self.get_tables()
        table_links = self.get_foreign_key_constraints()

        for table in tables:
            if table_docname := frappe.db.get_value(
                "Table",
                {
                    "data_source": self.name,
                    "table": table.get("table"),
                },
                "name",
            ):
                doc = frappe.get_doc("Table", table_docname)
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "Table",
                        "data_source": self.name,
                        "table": table.get("table"),
                        "label": table.get("label"),
                    }
                )

            for table_link in table_links.get(table.get("label"), []):
                if not doc.get("table_links", table_link):
                    doc.append("table_links", table_link)

            doc.save()

    def get_columns(self, table):
        if not table:
            return []

        columns = self.execute_query(
            """
                select column_name, data_type
                from information_schema.columns
                where table_name = %s order by column_name
            """,
            values=table.get("table"),
            as_dict=1,
        )

        # TODO: caching
        _columns = [
            {
                "table": table.get("table"),
                "column": d.get("column_name"),
                "table_label": table.get("label"),
                "type": d.get("data_type").title(),
                "label": frappe.unscrub(d.get("column_name")).rstrip().lstrip(),
            }
            for d in columns
        ]

        return _columns

    def get_distinct_column_values(self, column, search_text, limit=50):
        Table = frappe.qb.Table(column.get("table"))
        Field = frappe.qb.Field(column.get("column"))
        query = (
            frappe.qb.from_(Table)
            .select(Field.as_("label"))
            .distinct()
            .select(Field.as_("value"))
            .where(Field.like(f"%{search_text}%"))
            .limit(limit)
            .get_sql()
        )

        values = self.execute_query(query, as_dict=1)

        # TODO: caching
        return values

    def get_foreign_key_constraints(self):
        if self.check_if_frappe_db():
            return self.build_frappe_constraints()
        return {}

    def build_frappe_constraints(self):
        # save Link Fields & Table Fields as ForeignKeyConstraints
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
        standard_links = self.execute_query(query, as_dict=1)

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
        custom_links = self.execute_query(query, as_dict=1)

        dynamic_links = self.get_dynamic_link_map()

        links = standard_links + custom_links

        foreign_links = {}
        for link in links:
            if link.get("fieldtype") == "Link":
                foreign_links.setdefault(link.get("options"), []).append(
                    {
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )
                foreign_links.setdefault(link.get("parent"), []).append(
                    {
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("options"),
                        "foreign_table_label": link.get("options"),
                    }
                )
            if link.get("fieldtype") == "Table":
                foreign_links.setdefault(link.get("parent"), []).append(
                    {
                        "foreign_key": "parent",
                        "foreign_table": "tab" + link.get("options"),
                        "foreign_table_label": link.get("options"),
                    }
                )
                foreign_links.setdefault(link.get("options"), []).append(
                    {
                        "foreign_key": "parent",
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )

        for doctype in dynamic_links:
            if not doctype:
                continue

            for link in dynamic_links.get(doctype):
                foreign_links.setdefault(doctype, []).append(
                    {
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )
                foreign_links.setdefault(link.get("parent"), []).append(
                    {
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + doctype,
                        "foreign_table_label": doctype,
                    }
                )

        return foreign_links

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
            dynamic_links += self.execute_query(query, as_dict=True)

        for df in dynamic_links:
            if df.issingle:
                dynamic_link_map.setdefault(df.parent, []).append(df)
            else:
                try:
                    links = self.execute_query(
                        """select distinct {options} from `tab{parent}`""".format(**df)
                    )
                    links = [l[0] for l in links]
                    for doctype in links:
                        dynamic_link_map.setdefault(doctype, []).append(df)
                except frappe.db.TableMissingError:  # noqa: E722
                    pass

        return dynamic_link_map

    def get_running_queries(self):
        query = f"""select
                id, user, db, command, time, state, info, progress
            from
                information_schema.processlist
            where
                user = "{self.username}"
                and db = "{self.database_name}"
                and info not like '%information_schema.processlist%'
            """
        processlist = self.execute_query(
            query,
            skip_validation=True,
            as_dict=True,
        )

        return processlist

    def kill_query(self, query_id):
        self.execute_query(f"kill {query_id}", skip_validation=True)


@contextmanager
def connect_to_db(db):
    try:
        db.connect()
        yield db
    except Exception as e:
        frappe.log_error(
            title="Error connecting to database",
            message=frappe.get_traceback(),
        )
        raise e
    finally:
        db.close()
