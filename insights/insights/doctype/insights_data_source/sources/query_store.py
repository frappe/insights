# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
from sqlalchemy import create_engine, text

from insights.insights.doctype.insights_data_source.sources.sqlite import SQLiteDB
from insights.insights.query_builders.sqlite.sqlite_query_builder import (
    SQLiteQueryBuilder,
)

from .utils import create_insights_table


class StoredQueryTableFactory:
    # a factory for creating table objects
    # creates a list of tables objects from a list of queries that are marked as stored
    def __init__(self) -> None:
        self.data_source = "Query Store"

    def sync_tables(self, connection, tables=None, force=False):
        self.connection = connection
        to_sync = self.get_stored_queries() if tables is None else tables
        for docname in to_sync:
            if not frappe.db.exists("Insights Query", docname):
                continue
            doc = frappe.get_doc("Insights Query", docname)
            # fetch results internally imports them into the db
            # also updates the insights table
            doc.fetch_results()
            force and create_insights_table(self.make_table(doc), force=True)

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
        database_path = frappe.get_site_path("private", "files", "insights_query_store.sqlite")
        self.engine = create_engine(f"sqlite:///{database_path}")
        self.table_factory = StoredQueryTableFactory()
        self.query_builder = SQLiteQueryBuilder(self.engine)

    def sync_tables(self, tables=None, force=False):
        with self.engine.begin() as connection:
            self.table_factory.sync_tables(connection, tables, force=force)

    def get_table_columns(self, table):
        query = frappe.get_doc("Insights Query", table)
        return query.get_columns()

    def store_query(self, query, results):
        if not results:
            with self.engine.begin() as connection:
                connection.execute(text(f"DROP TABLE IF EXISTS '{query.name}'"))
                return

        create_insights_table(self.table_factory.make_table(query))
        columns = [col["label"] for col in results[0]]
        df = pd.DataFrame(results[1:], columns=columns, dtype=str)
        df.to_sql(query.name, self.engine, if_exists="replace", index=False)


def sync_query_store(tables=None, force=False):
    query_store = QueryStore()
    query_store.sync_tables(tables, force)


def store_query(query, results):
    query_store = QueryStore()
    query_store.store_query(query, results)


def remove_stored_query(query):
    query_store = QueryStore()
    query_store.store_query(query, [])
    frappe.db.delete("Insights Table", {"table": query.name, "data_source": "Query Store"})
