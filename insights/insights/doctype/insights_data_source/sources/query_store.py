# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re
import frappe
from .models import BaseDataSource
from .utils import create_insights_table
from frappe.database.mariadb.database import MariaDBDatabase
from insights.insights.query_builders.frappe_qb import FrappeQueryBuilder
from insights.insights.doctype.insights_table_import.insights_table_import import (
    make_column_def,
)


class StoredQueryTableFactory:
    # a factory for creating table objects
    # creates a list of tables objects from a list of queries that are marked as stored
    def __init__(self) -> None:
        self.data_source = "Query Store"

    def get_tables(self, queries=None):
        # create table object from the stored queries
        tables = []
        for query in self.get_stored_queries(queries):
            doc = frappe.get_doc("Insights Query", query.name)
            columns = doc.get_columns()
            tables.append(
                frappe._dict(
                    {
                        "table": doc.name,
                        "label": doc.title,
                        "data_source": self.data_source,
                        "columns": self.get_columns(columns),
                    }
                )
            )
        return tables

    def get_stored_queries(self, queries=None):
        # get all queries that are marked as stored
        filters = {"is_stored": 1}
        if queries:
            filters["name"] = ("in", queries)
        return frappe.get_all("Insights Query", filters=filters, pluck="name")

    def get_columns(self, columns):
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


class QueryStore(BaseDataSource):
    def __init__(self):
        self.conn: MariaDBDatabase = MariaDBDatabase()
        self.query_builder: FrappeQueryBuilder = FrappeQueryBuilder()
        self.table_factory: StoredQueryTableFactory = StoredQueryTableFactory()

    def test_connection(self):
        return True

    def build_query(self, query):
        # converts insights query to a sql query
        return self.query_builder.build(query)

    def execute_query(self, query, *args, **kwargs):
        self.validate_query(query)
        self.create_temporary_tables(query)
        result = self._execute(query, *args, **kwargs)
        self.conn.close()
        return result

    def sync_tables(self, queries=None, force=False):
        for table in self.table_factory.get_tables(queries=queries):
            create_insights_table(table, force=force)

    def create_temporary_tables(self, query):
        tables = re.findall(r"from\s+`?([a-zA-Z0-9_-]+)`?", query, re.IGNORECASE)
        for table in tables:
            self.create_temporary_table(table)

    def create_temporary_table(self, table):
        if not frappe.db.exists("Insights Query", table):
            return

        # create temporary table for an existing insights query
        query = frappe.get_doc("Insights Query", table)
        columns = query.get_columns()
        result = query.load_result()

        _columns = []
        for row in columns:
            _columns.append(make_column_def(row.column, row.type))

        if "TEMPID" not in _columns[0]:
            _columns = ["TEMPID INT PRIMARY KEY AUTO_INCREMENT"] + _columns

        create_table = f"CREATE TEMPORARY TABLE `{query.name}`({', '.join(_columns)})"

        rows = []
        for i, row in enumerate(result):
            rows.append([i + 1] + list(row))
        insert_records = (
            f"INSERT INTO `{query.name}` VALUES {', '.join(['%s'] * len(rows))}"
        )

        self._execute(create_table)
        # since "create temporary table" doesn't cause an implict commit
        # to avoid "implicit commit" error from frappe/database.py -> check_implict_commit
        self.conn.transaction_writes -= 1
        self._execute(insert_records, values=rows)

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

    def describe_table(self, table, limit=20):
        self.create_temporary_table(table)
        columns = self._execute(f"""desc `{table}`""")
        data = self._execute(f"""select * from `{table}` limit {limit}""")
        no_of_rows = self._execute(f"""select count(*) from `{table}`""")[0][0]
        self.conn.close()
        return columns, data, no_of_rows

    def get_distinct_column_values(self, column, search_text=None, limit=25):
        if not frappe.db.exists("Insights Query", column.get("table")):
            return []

        query = frappe.get_cached_doc("Insights Query", column.get("table"))
        Table = frappe.qb.Table(column.get("table"))
        Column = frappe.qb.Field(column.get("column"))
        query = frappe.qb.from_(Table).select(Column).distinct().limit(limit)
        if search_text:
            query = query.where(Column.like(f"%{search_text}%"))

        return self.execute_query(query.get_sql())
