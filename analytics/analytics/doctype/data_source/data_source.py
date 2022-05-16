# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.database.mariadb.database import MariaDBDatabase
from frappe.model.document import Document


class DataSource(Document):
    def before_save(self):
        if self.test_connection():
            self.status = "Active"
        else:
            self.status = "Inactive"

    def create_db_instance(self):
        if hasattr(self, "db_instance") and self.db_instance:
            return

        if self.database_type != "MariaDB":
            raise NotImplementedError

        if self.database_type == "MariaDB":
            self.db_instance = MariaDBDatabase(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.get_password(),
            )

    @frappe.whitelist()
    def test_connection(self):
        self.create_db_instance()
        self.db_instance.connect()
        user_exists = self.db_instance.a_row_exists("User")
        self.db_instance.close()
        if user_exists:
            frappe.msgprint("Connection Successful", alert=True)
            return True

    @frappe.whitelist()
    def import_tables(self):
        tables = self.get_tables()
        table_links = self.get_foreign_key_constraints()

        for table in tables:
            if frappe.db.exists(
                "Table",
                {
                    "data_source": self.name,
                    "table": table.get("table"),
                },
            ):
                continue

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

    def get_foreign_key_constraints(self):
        # save Link Fields & Table Fields as ForeignKeyConstraints
        self.create_db_instance()
        self.db_instance.connect()
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
        links = self.db_instance.sql(query, as_dict=1)
        self.db_instance.close()

        foreign_links = {}
        for link in links:
            if link.get("fieldtype") == "Link":
                foreign_links.setdefault(link.get("options"), []).append(
                    {
                        "foreign_table": link.get("parent"),
                        "foreign_key": link.get("fieldname"),
                    }
                )
            if link.get("fieldtype") == "Table":
                foreign_links.setdefault(link.get("parent"), []).append(
                    {
                        "foreign_table": link.get("options"),
                        "foreign_key": "parent",
                    }
                )

        return foreign_links

    def execute(self, query, debug=False):
        if not query:
            return

        self.create_db_instance()
        self.db_instance.connect()
        result = self.db_instance.sql(query, debug=debug)
        self.db_instance.close()

        return result

    def get_tables(self):
        self.create_db_instance()
        self.db_instance.connect()
        tables = self.db_instance.get_tables(cached=False)
        self.db_instance.close()

        # TODO: caching
        _tables = [
            {
                "table": table,
                "label": table.replace("tab", ""),
            }
            for table in list(tables)
        ]
        return _tables

    def get_columns(self, table):
        if not table:
            return []

        self.create_db_instance()
        self.db_instance.connect()
        columns = self.db_instance.sql(
            """
                select column_name, data_type
                from information_schema.columns
                where table_name = %s order by column_name
            """,
            table.get("table"),
            as_dict=1,
        )
        self.db_instance.close()

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
        self.create_db_instance()
        self.db_instance.connect()

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

        values = self.db_instance.sql(query, as_dict=1)

        self.db_instance.close()

        # TODO: caching
        return values
