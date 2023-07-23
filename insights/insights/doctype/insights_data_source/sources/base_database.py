# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import ClauseElement

from insights.insights.doctype.insights_table_import.insights_table_import import (
    InsightsTableImport,
)
from insights.utils import ResultColumn

from .utils import (
    add_limit_to_sql,
    cache_results,
    compile_query,
    execute_and_log,
    get_cached_results,
    replace_query_tables_with_cte,
)


class DatabaseConnectionError(frappe.ValidationError):
    pass


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
        except BaseException as e:
            frappe.log_error(title="Error connecting to database", message=e)
            raise DatabaseConnectionError(e)

    def build_query(self, query, with_cte=False):
        """Build insights query and return the sql"""
        query_str = self.query_builder.build(query, dialect=self.engine.dialect)
        if with_cte and frappe.db.get_single_value("Insights Settings", "allow_subquery"):
            query_str = replace_query_tables_with_cte(query_str, self.data_source)
        return query_str if query_str else None

    def run_query(self, query):
        """Run insights query and return the result"""
        sql = self.build_query(query)
        if sql is None:
            return []
        if frappe.db.get_single_value("Insights Settings", "allow_subquery"):
            sql = replace_query_tables_with_cte(sql, self.data_source)
        # set a hard max limit to prevent long running queries
        max_rows = frappe.db.get_single_value("Insights Settings", "query_result_limit") or 1000
        sql = add_limit_to_sql(sql, max_rows)
        return self.execute_query(sql, return_columns=True, is_native_query=query.is_native_query)

    def execute_query(
        self,
        sql,
        pluck=False,
        return_columns=False,
        replace_query_tables=False,
        is_native_query=False,
        cached=False,
    ):
        if sql is None:
            return []

        sql = self.compile_if_needed(sql, is_native_query)
        sql = self.process_subquery(sql, replace_query_tables)
        sql = self.escape_special_characters(sql) if is_native_query else sql

        self.validate_native_sql(sql)

        if cached:
            cached_results = get_cached_results(sql, self.data_source)
            if cached_results:
                return cached_results

        with self.connect() as connection:
            res = execute_and_log(connection, sql, self.data_source)
            cols = [ResultColumn.from_args(d[0]) for d in res.cursor.description]
            rows = [list(r) for r in res.fetchall()]
            rows = [r[0] for r in rows] if pluck else rows
            ret = [cols] + rows if return_columns else rows
            cached and cache_results(sql, self.data_source, ret)
            return ret

    def compile_if_needed(self, sql, is_native_query):
        if isinstance(sql, ClauseElement) and not is_native_query:
            # since db.execute() is also being used with Query objects i.e non-compiled queries
            compiled = compile_query(sql, self.engine.dialect)
            sql = str(compiled) if compiled else None
        return sql

    def process_subquery(self, sql, replace_query_tables):
        allow_subquery = frappe.db.get_single_value("Insights Settings", "allow_subquery")
        if replace_query_tables and allow_subquery:
            sql = replace_query_tables_with_cte(sql, self.data_source)
        return sql

    def escape_special_characters(self, sql):
        # to fix special characters in query like %
        return text(sql.replace("%%", "%"))

    def validate_native_sql(self, query):
        select_or_with = str(query).strip().lower().startswith(("select", "with"))
        if not select_or_with:
            frappe.throw("Only SELECT and WITH queries are allowed")

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
