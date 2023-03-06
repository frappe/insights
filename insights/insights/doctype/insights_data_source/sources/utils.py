# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import sqlparse
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.pool import NullPool

MARIADB_TO_GENERIC_TYPES = {
    "int": "Integer",
    "bigint": "Long Int",
    "decimal": "Decimal",
    "text": "Text",
    "longtext": "Long Text",
    "date": "Date",
    "datetime": "Datetime",
    "time": "Time",
    "varchar": "String",
}


def get_sqlalchemy_engine(**kwargs) -> Engine:

    dialect = kwargs.pop("dialect")
    driver = kwargs.pop("driver")
    user = kwargs.pop("username")
    password = kwargs.pop("password")
    database = kwargs.pop("database")
    host = kwargs.pop("host", "localhost")
    port = kwargs.pop("port") or 3306
    extra_params = "&".join([f"{k}={v}" for k, v in kwargs.items()])

    uri = f"{dialect}+{driver}://{user}:{password}@{host}:{port}/{database}?{extra_params}"

    # TODO: cache the engine by uri
    return create_engine(uri, poolclass=NullPool)


def create_insights_table(table, force=False):
    exists = frappe.db.exists(
        "Insights Table",
        {
            "data_source": table.data_source,
            "table": table.table,
            "is_query_based": table.is_query_based,
        },
    )

    if docname := exists:
        doc = frappe.get_doc("Insights Table", docname)
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Insights Table",
                "data_source": table.data_source,
                "table": table.table,
                "label": table.label,
                "is_query_based": table.is_query_based,
            }
        )

    doc.label = table.label
    if force:
        doc.columns = []
        doc.table_links = []

    for table_link in table.table_links or []:
        if not doc.get("table_links", table_link):
            doc.append("table_links", table_link)

    for column in table.columns or []:
        # do not overwrite existing columns, since type or label might have been changed
        if any([doc_column.column == column.column for doc_column in doc.columns]):
            print("skipping", column.column)
            continue
        doc.append("columns", column)

    column_names = [c.column for c in table.columns]
    for column in doc.columns:
        if column.column not in column_names:
            doc.remove(column)

    # need to ignore permissions when creating/updating a table in query store
    # a user may have access to create a query and store it, but not to create a table
    doc.save(ignore_permissions=force)
    return doc.name


def parse_sql_tables(sql):
    parsed = sqlparse.parse(sql)
    tables = []
    identifier = None
    for statement in parsed:
        for token in statement.tokens:
            if token.ttype is sqlparse.tokens.Keyword and token.value.lower() in [
                "from",
                "join",
            ]:
                identifier = token.value.lower()
            if identifier and isinstance(token, sqlparse.sql.Identifier):
                tables.append(token.get_real_name())
                identifier = None
            if identifier and isinstance(token, sqlparse.sql.IdentifierList):
                for item in token.get_identifiers():
                    tables.append(item.get_real_name())
                identifier = None

    return [strip_quotes(table) for table in tables]


def get_stored_query_sql(query, data_source=None, verbose=False):
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

    tables = parse_sql_tables(query)
    queries = frappe.get_all(
        "Insights Query",
        filters={"name": ("in", tables)},
        fields=["name", "sql", "data_source"],
    )
    if not queries:
        return None

    # queries = [
    #     { "name": "QRY-001", "sql": "SELECT name FROM `QRY-004`", "data_source": "Query Store" },
    #     { "name": "QRY-002","sql": "SELECT name FROM `Customer`","data_source": "Demo" },
    #     { "name": "QRY-003","sql": "SELECT name FROM `Supplier`","data_source": "Demo" },
    # ]
    stored_query_sql = {}
    for query in queries:
        if data_source is None:
            data_source = query.data_source
        if data_source and query.data_source != data_source:
            frappe.throw(
                "Cannot use queries from different data sources in a single query"
            )

        stored_query_sql[query.name] = query.sql
        sub_stored_query_sql = get_stored_query_sql(query.sql, data_source)
        # sub_stored_query_sql = { 'QRY-004': 'SELECT name FROM `Item`' }
        if not sub_stored_query_sql:
            continue

        cte = "WITH"
        for table, sub_query in sub_stored_query_sql.items():
            cte += f" `{table}` AS ({sub_query}),"
        cte = cte[:-1]
        stored_query_sql[query.name] = f"{cte} {query.sql}"

    return stored_query_sql


def process_cte(main_query):
    """
    Replaces stored queries in the main query with the actual query using CTE
    """

    stored_query_sql = get_stored_query_sql(main_query)
    if not stored_query_sql:
        return None

    # stored_query_sql is a dict of table name and query
    # for example, if the query is
    # SELECT * FROM `QRY-001`
    # LEFT JOIN `QRY-002` ON `QRY-001`.`name` = `QRY-002`.`name`

    # and the sql for
    # - `QRY-001` is SELECT name FROM `QRY-004`
    # - `QRY-002` is SELECT name FROM `Customer`
    # - `QRY-004` is SELECT name FROM `Item`

    # then the stored_query_sql will be
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
    cte = "WITH"
    for query_name, sql in stored_query_sql.items():
        cte += f" `{query_name}` AS ({sql}),"
    cte = cte[:-1]
    return cte + " " + main_query


def strip_quotes(table):
    if (
        (table.startswith("`") and table.endswith("`"))
        or (table.startswith('"') and table.endswith('"'))
        or (table.startswith("'") and table.endswith("'"))
    ):
        return table[1:-1]
    return table


def add_limit_to_sql(sql, limit):
    stripped_sql = sql.strip().rstrip(";")
    return f"WITH limited AS ({stripped_sql}) SELECT * FROM limited LIMIT {limit};"
