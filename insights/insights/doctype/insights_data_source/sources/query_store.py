# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from .models import BaseDatabase
from .utils import create_insights_table
from frappe.database.mariadb.database import MariaDBDatabase
from insights.insights.query_builders.sql_builder import SQLQueryBuilder
from insights.insights.doctype.insights_table_import.insights_table_import import (
    make_column_def,
)


class StoredQueryTableFactory:
    # a factory for creating table objects
    # creates a list of tables objects from a list of queries that are marked as stored
    def __init__(self) -> None:
        self.data_source = "Query Store"

    def get_tables(self, queries=None):
        tables = []
        # create table object from the stored queries
        for docname in queries or self.get_stored_queries():
            doc = frappe.get_doc("Insights Query", docname)
            tables.append(self.make_table(doc))
        return tables

    def make_table(self, query):
        return frappe._dict(
            {
                "table": query.name,
                "label": query.title,
                "data_source": self.data_source,
                "columns": self.make_columns(query.get_columns()),
            }
        )

    def get_stored_queries(self):
        # get all queries that are marked as stored
        return frappe.get_all("Insights Query", filters={"is_stored": 1}, pluck="name")

    def make_columns(self, columns):
        return [
            frappe._dict(
                {
                    "column": column.column or column.label,
                    "label": column.label,
                    "type": column.type,
                }
            )
            for column in columns
        ]


class QueryStore(BaseDatabase):
    def __init__(self):
        self.conn: MariaDBDatabase = MariaDBDatabase()
        self.query_builder: SQLQueryBuilder = SQLQueryBuilder()
        self.table_factory: StoredQueryTableFactory = StoredQueryTableFactory()

    def test_connection(self):
        return True

    def build_query(self, query):
        # converts insights query to a sql query
        return self.query_builder.build(query)

    def run_query(self, query):
        # runs insights query
        self.create_temporary_tables(query.get_selected_tables())
        return self.execute_query(self.build_query(query))

    def execute_query(self, query, *args, **kwargs):
        self.validate_query(query)
        result = self._execute(query, *args, **kwargs)
        self.conn.close()
        return result

    def sync_tables(self, queries=None, force=False):
        for table in self.table_factory.get_tables(queries=queries):
            create_insights_table(table, force=force)

    def create_temporary_tables(self, query_tables):
        for table in query_tables:
            self.create_temporary_table(table.table)

    def create_temporary_table(self, table):
        if not frappe.db.exists("Insights Query", table):
            return

        # create temporary table for an existing insights query
        query = frappe.get_doc("Insights Query", table)
        columns = query.get_columns()
        result = list(query.load_result())
        result.pop(0)

        _columns = []
        for row in columns:
            _columns.append(make_column_def(row.column or row.label, row.type))

        create_table = f"CREATE TEMPORARY TABLE `{query.name}`({', '.join(_columns)})"

        insert_records = (
            f"INSERT INTO `{query.name}` VALUES {', '.join(['%s'] * len(result))}"
        )

        self._execute(create_table)
        # since "create temporary table" doesn't cause an implict commit
        # to avoid "implicit commit" error from frappe/database.py -> check_implict_commit
        self.conn.transaction_writes -= 1
        self._execute(insert_records, values=result)

    def validate_query(self, query):
        if not query.strip().lower().startswith("select"):
            raise frappe.ValidationError(
                "Only SELECT statements are allowed in Query Store"
            )

    def _execute(self, query: str, *args, **kwargs):
        # doesn't close the connection after execution
        try:
            return self.conn.sql(query, *args, **kwargs)
        except Exception as e:
            # close the connection if there is an error
            self.conn.close()
            frappe.log_error(f"Error fetching data from QueryStore: {e}")
            raise

    def get_table_preview(self, table, limit=20):
        self.create_temporary_table(table)
        data = self._execute(f"""select * from `{table}` limit {limit}""")
        length = self._execute(f"""select count(*) from `{table}`""")[0][0]
        self.conn.close()
        return {
            "data": data or [],
            "length": length or 0,
        }

    def get_column_options(self, table, column, search_text=None, limit=25):
        if not frappe.db.exists("Insights Query", table):
            return []

        query = frappe.get_cached_doc("Insights Query", table)
        Table = frappe.qb.Table(table)
        Column = frappe.qb.Field(column)
        query = frappe.qb.from_(Table).select(Column).distinct().limit(limit)
        if search_text:
            query = query.where(Column.like(f"%{search_text}%"))

        return self.execute_query(query.get_sql())

    def get_table_columns(self, table):
        if not frappe.db.exists("Insights Query", table):
            return []

        query = frappe.get_cached_doc("Insights Query", table)
        return query.get_columns()
