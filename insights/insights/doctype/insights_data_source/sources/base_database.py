# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights.insights.doctype.insights_table_import.insights_table_import import (
    InsightsTableImport,
)

from .utils import (
    Timer,
    add_limit_to_sql,
    compile_query,
    create_execution_log,
    replace_query_tables_with_cte,
)


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

    def build_query(self, query) -> str:
        query_str = self.query_builder.build(query, dialect=self.engine.dialect)
        return query_str or ""

    def run_query(self, query):
        sql = self.build_query(query)
        if not sql:
            return []
        if frappe.db.get_single_value("Insights Settings", "allow_subquery"):
            sql = replace_query_tables_with_cte(sql, self.data_source)
        if query.is_native_query:
            sql = add_limit_to_sql(sql, query.limit)
        # set a hard max limit to prevent long running queries
        sql = add_limit_to_sql(
            sql,
            frappe.db.get_single_value("Insights Settings", "query_result_limit")
            or 1000,
        )
        return self.execute_query(sql, with_columns=True)

    def validate_query(self, query):
        select_or_with = str(query).strip().lower().startswith(("select", "with"))
        if not select_or_with:
            frappe.throw("Only SELECT and WITH queries are allowed")

    def execute_query(
        self, query, pluck=False, with_columns=False, replace_query_tables=False
    ):
        if query is None:
            return []
        if not isinstance(query, str):
            query = compile_query(query, self.engine.dialect)
        if replace_query_tables and frappe.db.get_single_value(
            "Insights Settings", "allow_subquery"
        ):
            query = replace_query_tables_with_cte(query, self.data_source)

        self.validate_query(query)
        with self.connect() as connection:
            with Timer() as t:
                res = connection.execute(query)
            create_execution_log(query, self.data_source, t.elapsed)
            columns = [f"{d[0]}::{d[1]}" for d in res.cursor.description]
            rows = [list(r) for r in res.fetchall()]
            rows = [r[0] for r in rows] if pluck else rows
            return [columns] + rows if with_columns else rows

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
