# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
import sqlparse
from sqlalchemy import create_engine

from insights.insights.doctype.insights_data_source.sources.sqlite import SQLiteDB
from insights.insights.query_builders.sqlite.sqlite_query_builder import (
    SQLiteQueryBuilder,
)

from .utils import create_insights_table, process_cte


class StoredQueryTableFactory:
    # a factory for creating table objects
    # creates a list of tables objects from a list of queries that are marked as stored
    def __init__(self) -> None:
        self.data_source = "Query Store"

    def import_query(self, query):
        result = query.load_results(fetch_if_not_exists=True)
        if not result:
            return
        columns = [r.split("::")[0] for r in result[0]]
        df = pd.DataFrame(result[1:], columns=columns)
        df.to_sql(query.name, self.connection, if_exists="replace", index=False)

    def sync_tables(self, connection, tables=None, force=False):
        self.connection = connection
        for table in self.get_tables(tables):
            create_insights_table(table, force=force)

    def get_tables(self, tables=None):
        _tables = []
        to_sync = self.get_stored_queries() if tables is None else tables
        # create table object from the stored queries
        for docname in to_sync:
            doc = frappe.get_doc("Insights Query", docname)
            # since we already have doc here, we can use it to import query result
            self.import_query(doc)
            _tables.append(self.make_table(doc))
        return _tables

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
                    "column": column.label,  # use label as column name
                    "label": column.label,
                    "type": column.type,
                }
            )
            for column in columns
        ]


class QueryStore(SQLiteDB):
    def __init__(self) -> None:
        self.data_source = "Query Store"
        database_path = frappe.get_site_path(
            "private", "files", "insights_query_store.sqlite"
        )
        self.engine = create_engine(f"sqlite:///{database_path}")
        self.table_factory = StoredQueryTableFactory()
        self.query_builder = SQLiteQueryBuilder()

    def sync_tables(self, tables=None, force=False):
        with self.engine.begin() as connection:
            self.table_factory.sync_tables(connection, tables, force=force)


def sync_query_store(tables=None, force=False):
    query_store = QueryStore()
    query_store.sync_tables(tables, force)
