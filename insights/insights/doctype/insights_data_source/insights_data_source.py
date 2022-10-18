# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from functools import cached_property
from frappe.model.document import Document

from .sources.models import BaseDataSource
from .sources.query_store import QueryStore
from .sources.frappe_db import is_frappe_db, FrappeDB, SiteDB

from insights.constants import SOURCE_STATUS
from insights.insights.doctype.insights_query.insights_query import InsightsQuery


class InsightsDataSource(Document):
    def before_insert(self):
        if self.is_site_db and frappe.db.exists(
            "Insights Data Source", {"is_site_db": 1}
        ):
            frappe.throw("Only one site database can be configured")

    def on_trash(self):
        if self.is_site_db:
            frappe.throw("Cannot delete the site database. It is needed for Insights.")
        if self.name == "Query Store":
            frappe.throw("Cannot delete the Query Store. It is needed for Insights.")

        linked_doctypes = ["Insights Table"]
        for doctype in linked_doctypes:
            for name in frappe.db.get_all(
                doctype, {"data_source": self.name}, pluck="name"
            ):
                frappe.delete_doc(doctype, name)

    @cached_property
    def db(self) -> BaseDataSource:
        if self.is_site_db:
            return SiteDB(data_source=self.name)
        if self.name == "Query Store":
            return QueryStore()
        return self.get_database()

    def get_database(self):
        conn_args = {
            "data_source": self.name,
            "host": self.host,
            "port": self.port,
            "use_ssl": self.use_ssl,
            "username": self.username,
            "password": self.get_password(),
            "database_name": self.database_name,
        }

        if is_frappe_db(conn_args):
            return FrappeDB(**conn_args)

        frappe.throw(f"Unsupported database type: {self.database_type}")

    def validate(self):
        if self.is_site_db or self.name == "Query Store":
            return
        self.db_connection_fields()

    def db_connection_fields(self):
        mandatory = ("host", "port", "username", "password", "database_name")
        for field in mandatory:
            if not self.get(field):
                frappe.throw(f"{field} is mandatory for Database")

    def before_save(self):
        self.status = (
            SOURCE_STATUS.Active if self.test_connection() else SOURCE_STATUS.Inactive
        )

    def test_connection(self):
        try:
            return self.db.test_connection()
        except Exception as e:
            frappe.log_error("Testing Data Source connection failed", e)
            return False

    def build_query(self, query: InsightsQuery):
        return self.db.build_query(query)

    def run_query(self, query: InsightsQuery):
        return self.db.execute_query(self.build_query(query))

    def sync_tables(self, *args, **kwargs):
        self.db.sync_tables(*args, **kwargs)

    def get_table_columns(self, table):
        return self.db.get_table_columns(table)

    def get_column_options(self, *args, **kwargs):
        return self.db.get_column_options(*args, **kwargs)

    def get_table_preview(self, table, limit=20):
        return self.db.get_table_preview(table, limit)
