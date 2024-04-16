# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re

import frappe
from sqlalchemy.sql import text

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


class DatabaseCredentialsError(frappe.ValidationError):
    pass


class DatabaseParallelConnectionError(frappe.ValidationError):
    pass


class Database:
    def test_connection(self):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def build_query(self, query):
        raise NotImplementedError

    def run_query(self, query):
        raise NotImplementedError

    def execute_query(self):
        raise NotImplementedError

    def sync_tables(self):
        raise NotImplementedError

    def get_table_columns(self):
        raise NotImplementedError

    def get_column_options(self):
        raise NotImplementedError

    def get_table_preview(self):
        raise NotImplementedError

    def table_exists(self, table: str):
        """
        While importing a csv file, check if the table exists in the database
        """
        raise NotImplementedError

    def import_table(self, import_doc: InsightsTableImport):
        """
        Imports the table into the database
        """
        raise NotImplementedError


class BaseDatabase(Database):
    def __init__(self):
        self.engine = None
        self.data_source = None
        self.connection = None
        self.query_builder = None
        self.table_factory = None

    def test_connection(self, log_errors=True):
        with self.connect(log_errors=log_errors) as connection:
            res = connection.execute(text("SELECT 1"))
            return res.fetchone()

    def connect(self, *, log_errors=True):
        try:
            return self.engine.connect()
        except Exception as e:
            log_errors and frappe.log_error("Error connecting to database")
            self.handle_db_connection_error(e)

    def handle_db_connection_error(self, e):
        raise DatabaseConnectionError(e) from e

    def build_query(self, query):
        """Used to update the sql in insights query"""
        query_str = self.query_builder.build(query)
        query_str = self.process_subquery(query_str) if not query.is_native_query else query_str
        return query_str

    def run_query(self, query):
        sql = self.query_builder.build(query)
        return self.execute_query(sql, return_columns=True, query_name=query.name)

    def execute_query(
        self,
        sql,  # can be a string or a sqlalchemy query object or text object
        pluck=False,
        return_columns=False,
        cached=False,
        query_name=None,
        log_errors=True,
    ):
        if sql is None:
            return []
        if isinstance(sql, str) and not sql.strip():
            return []

        sql = self.compile_query(sql)
        sql = self.process_subquery(sql)
        sql = self.set_row_limit(sql)
        sql = self.replace_template_tags(sql)
        sql = self.escape_special_characters(sql)

        self.validate_native_sql(sql)

        if cached:
            cached_results = get_cached_results(sql, self.data_source)
            if cached_results:
                return cached_results

        with self.connect(log_errors=log_errors) as connection:
            res = execute_and_log(connection, sql, self.data_source, query_name)
            cols = [ResultColumn.from_args(d[0]) for d in res.cursor.description]
            rows = [list(r) for r in res.fetchall()]
            rows = [r[0] for r in rows] if pluck else rows
            ret = [cols] + rows if return_columns else rows
            cached and cache_results(sql, self.data_source, ret)
            return ret

    def compile_query(self, query):
        if hasattr(query, "compile"):
            compiled = compile_query(query, self.engine.dialect)
            query = str(compiled) if compiled else None
        return query

    def process_subquery(self, sql):
        allow_subquery = frappe.db.get_single_value("Insights Settings", "allow_subquery")
        if allow_subquery:
            sql = replace_query_tables_with_cte(sql, self.data_source, self.engine.dialect)
        return sql

    def escape_special_characters(self, sql):
        # to fix special characters in query like %
        if self.engine.dialect.name in ("mysql", "postgresql"):
            sql = re.sub(r"(%{1,})", r"%%", sql)
        return sql

    def replace_template_tags(self, sql):
        # replace template tags with actual values
        # {{ QRY_1203 }} -> SELECT * FROM `tabSales Invoice`
        # find all the template tags in the query
        # match all character between {{ and }}
        matches = re.findall(r"{{(.*?)}}", sql)
        if not matches:
            return sql
        context = {}
        for match in matches:
            query_name = match.strip().replace("_", "-")
            if (
                not query_name
                or not query_name.startswith("QRY")
                or not frappe.db.exists("Insights Query", query_name)
            ):
                continue
            query = frappe.get_doc("Insights Query", query_name)
            key = query_name.replace("-", "_")
            context[key] = self.build_query(query)
        sql = frappe.render_template(sql, context)
        return sql

    def set_row_limit(self, sql):
        # set a hard max limit to prevent long running queries
        # there's no use case to view more than 500 rows in the UI
        # TODO: while exporting as csv, we can remove this limit
        max_rows = frappe.db.get_single_value("Insights Settings", "query_result_limit") or 500
        return add_limit_to_sql(sql, max_rows)

    def validate_native_sql(self, query):
        select_or_with = str(query).strip().lower().startswith(("select", "with"))
        if not select_or_with:
            frappe.throw("Only SELECT and WITH queries are allowed")
