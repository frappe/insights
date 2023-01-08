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

from .utils import create_insights_table


class StoredQueryTableFactory:
    # a factory for creating table objects
    # creates a list of tables objects from a list of queries that are marked as stored
    def __init__(self) -> None:
        self.data_source = "Query Store"

    def import_query(self, query):
        result = frappe.parse_json(query.results)
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
        # create table object from the stored queries
        for docname in tables or self.get_stored_queries():
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
        database_path = frappe.get_site_path(
            "private", "files", "insights_query_store.sqlite"
        )
        self.engine = create_engine(f"sqlite:///{database_path}")
        self.table_factory = StoredQueryTableFactory()
        self.query_builder = SQLiteQueryBuilder()

    def sync_tables(self, tables=None, force=False):
        with self.engine.begin() as connection:
            self.table_factory.sync_tables(connection, tables, force=force)

    def execute_query(self, query, pluck=False):
        try:
            table_query_map, data_source = get_table_query_map(query)
        except Exception:
            frappe.log_error(title="Query Store: Invalid Query")
            return super().execute_query(query, pluck=pluck)

        if not table_query_map or not frappe.db.get_single_value(
            "Insights Settings", "use_cte"
        ):
            return super().execute_query(query, pluck=pluck)
        else:
            # table_query_map is a dict of table name and query
            # for example, if the query is
            # SELECT * FROM `QRY-001`
            # LEFT JOIN `QRY-002` ON `QRY-001`.`name` = `QRY-002`.`name`

            # and the sql for
            # - `QRY-001` is SELECT name FROM `QRY-004`
            # - `QRY-002` is SELECT name FROM `Customer`
            # - `QRY-004` is SELECT name FROM `Item`

            # then the table_query_map will be
            # {
            #   'QRY-001': 'WITH `QRY-004` AS (SELECT name FROM `Item`) SELECT name FROM `QRY-004`',
            #   'QRY-002': 'SELECT name FROM `Customer`',
            # }

            # the query will be replaced with
            # WITH
            #   `QRY-001` AS (
            #       WITH `QRY-004` AS (SELECT name FROM `Item`) SELECT name FROM `QRY-004`
            #   ),
            #   `QRY-002` AS (SELECT name FROM `Customer`)
            # SELECT * FROM `QRY-001`
            # LEFT JOIN `QRY-002` ON `QRY-001`.`name` = `QRY-002`.`name`

            # append the WITH clause to the query
            cte = "WITH " + ", ".join(
                [f"`{table}` AS ({query})" for table, query in table_query_map.items()]
            )
            query = cte + " " + query

            # execute the query in the data source
            doc = frappe.get_doc("Insights Data Source", data_source)
            frappe.log_error(
                title=f"Query Store: {data_source}",
                message=sqlparse.format(query, reindent=True, keyword_case="upper"),
            )
            return doc.execute_query(query, pluck=pluck)


def sync_query_store(tables=None, force=False):
    query_store = QueryStore()
    query_store.sync_tables(tables, force)


def find_tables_in_query(query: str):
    """
    Takes a native sql query and returns a list of tables used in the query

    For example, if the query is
    SELECT * FROM `QRY-001`
    LEFT JOIN `QRY-002` ON `QRY-001`.`name` = `QRY-002`.`name`
    LEFT JOIN `QRY-003` ON `QRY-001`.`name` = `QRY-003`.`name`

    returns ['QRY-001', 'QRY-002', 'QRY-003']

    Also, if the query is
    SELECT * FROM `QRY-001` as t0
    LEFT JOIN `QRY-002` as t1 ON t0.`name` = t1.`name`
    LEFT JOIN `QRY-003` as t2 ON t0.`name` = t2.`name`

    returns ['QRY-001', 'QRY-002', 'QRY-003']
    """

    parsed = sqlparse.parse(query)
    tables = []
    for token in parsed[0].tokens:
        if isinstance(token, sqlparse.sql.Identifier):
            tables.append(token.get_real_name())
    return tables


def get_table_query_map(query, data_source=None, verbose=False):
    """
    Takes a native sql query and returns a map of table name to the query along with the subqueries

    For example, if the query is
    SELECT * FROM `QRY-001`
    LEFT JOIN `QRY-002` ON `QRY-001`.`name` = `QRY-002`.`name`
    LEFT JOIN `QRY-003` ON `QRY-001`.`name` = `QRY-003`.`name`

    and QRY-001 = SELECT name FROM `QRY-004`
    and QRY-002 = SELECT name FROM `Customer`
    and QRY-003 = SELECT name FROM `Supplier`
    and QRY-004 = SELECT name FROM `Item`

    Then the returned map will be
    {
        'QRY-001': 'WITH `QRY-004` AS (SELECT name FROM `Item`) SELECT name FROM `QRY-004`',
        'QRY-002': 'SELECT name FROM `Customer`',
        'QRY-003': 'SELECT name FROM `Supplier)'
    }

    If any one of the table belongs to any other data source
    then stop and return None
    """

    query_tables = find_tables_in_query(query)
    if verbose:
        print(f"tables in query {query}: {query_tables}")
    queries = frappe.get_all(
        "Insights Query",
        filters={"name": ("in", query_tables)},
        fields=["name", "sql", "data_source"],
    )
    # queries = [
    #     { "name": "QRY-001", "sql": "SELECT name FROM `QRY-004`", "data_source": "Query Store" },
    #     { "name": "QRY-002","sql": "SELECT name FROM `Customer`","data_source": "Demo" },
    #     { "name": "QRY-003","sql": "SELECT name FROM `Supplier`","data_source": "Demo" },
    # ]
    table_query_map = {}
    for query in queries:
        if query.data_source != "Query Store":
            if data_source is None:
                data_source = query.data_source
            if data_source and query.data_source != data_source:
                return None
        table_query_map[query.name] = query.sql

        if query.data_source == "Query Store":
            sub_table_query_map, _ = get_table_query_map(query.sql, data_source)
            # sub_table_query_map = { 'QRY-004': 'SELECT name FROM `Item`' }
            if not sub_table_query_map:
                return None

            cte = "WITH"
            for table, sub_query in sub_table_query_map.items():
                cte += f" `{table}` AS ({sub_query}),"
            cte = cte[:-1]
            table_query_map[query.name] = f"{cte} {query.sql}"

    return table_query_map, data_source
