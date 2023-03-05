# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights.insights.doctype.insights_table_import.insights_table_import import (
    InsightsTableImport,
)

from .utils import process_cte


class BaseDatabase:
    def __init__(self):
        self.engine = None
        self.data_source = None
        self.connection = None
        self.query_builder = None
        self.table_factory = None

    def test_connection(self):
        return self.execute_query("SELECT 1")

    def connect(self):
        try:
            return self.engine.connect()
        except Exception as e:
            frappe.log_error(title="Error connecting to database", message=e)
            frappe.throw("Error connecting to database")

    def build_query(self, query):
        query_str = self.query_builder.build(query, dialect=self.engine.dialect)
        if not query_str:
            return None

        query_with_cte = None
        if frappe.db.get_single_value("Insights Settings", "allow_subquery"):
            try:
                query_with_cte = process_cte(query_str)
            except Exception:
                frappe.log_error(title=f"Failed to process CTE: {query_str}")
                frappe.throw("Failed to process stored query as CTE.")
        return query_with_cte or query_str

    def run_query(self, query):
        return self.execute_query(self.build_query(query))

    def validate_query(self, query):
        select_or_with = str(query).strip().lower().startswith(("select", "with"))
        if not select_or_with:
            frappe.throw("Only SELECT and WITH queries are allowed")

    def execute_query(self, query, pluck=False):
        if query is None:
            return []
        self.validate_query(query)
        with self.connect() as connection:
            result = connection.execute(query).fetchall()
            return [r[0] for r in result] if pluck else [list(r) for r in result]

    def table_exists(self, table: str):
        """
        While importing a table, check if the table exists in the database
        """
        raise NotImplementedError

    def import_table(self, import_doc: InsightsTableImport):
        """
        Imports the table into the database
        """
        raise NotImplementedError

    def sync_tables(self):
        raise NotImplementedError

    def get_table_columns(self, table):
        raise NotImplementedError

    def get_column_options(self, table, column, search_text=None, limit=50):
        raise NotImplementedError

    def get_table_preview(self):
        raise NotImplementedError
