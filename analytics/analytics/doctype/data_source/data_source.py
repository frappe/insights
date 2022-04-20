# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.database.mariadb.database import MariaDBDatabase
from frappe.model.document import Document


class DataSource(Document):
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
                password=self.password,
            )

    @frappe.whitelist()
    def test_connection(self):
        self.create_db_instance()
        self.db_instance.connect()
        user_exists = self.db_instance.a_row_exists("User")
        self.db_instance.close()
        if user_exists:
            frappe.msgprint("Connection Successful", alert=True)

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

        values = self.db_instance.sql(query, as_dict=1, debug=1)

        self.db_instance.close()

        # TODO: caching
        return values
