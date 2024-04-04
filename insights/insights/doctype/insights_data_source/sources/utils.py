# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import time
from typing import TYPE_CHECKING, Callable, Optional
from urllib import parse

import frappe
import sqlparse
from frappe.utils.data import flt
from sqlalchemy import NullPool, create_engine
from sqlalchemy.engine.base import Engine

from insights.cache_utils import make_digest

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect


def get_sqlalchemy_engine(connect_args=None, **kwargs) -> Engine:
    connect_args = connect_args or {}

    if kwargs.get("connection_string"):
        return create_engine(
            kwargs.pop("connection_string"),
            poolclass=NullPool,
            connect_args=connect_args,
            **kwargs,
        )

    dialect = kwargs.pop("dialect")
    driver = kwargs.pop("driver")
    user = kwargs.pop("username")
    password = parse.quote(kwargs.pop("password"))
    database = kwargs.pop("database")
    host = kwargs.pop("host", "localhost")
    port = kwargs.pop("port") or 3306
    extra_params = "&".join(f"{k}={v}" for k, v in kwargs.items())

    uri = f"{dialect}+{driver}://{user}:{password}@{host}:{port}/{database}?{extra_params}"

    # TODO: cache the engine by uri
    return create_engine(uri, poolclass=NullPool, connect_args={})


def create_insights_table(table, force=False):
    exists = frappe.db.exists(
        "Insights Table",
        {
            "data_source": table.data_source,
            "table": table.table,
            "is_query_based": table.is_query_based or 0,
        },
    )

    doc_before = None
    if docname := exists:
        doc = frappe.get_doc("Insights Table", docname)
        # using doc.get_doc_before_save() doesn't work here
        doc_before = frappe.get_cached_doc("Insights Table", docname)
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Insights Table",
                "data_source": table.data_source,
                "table": table.table,
                "label": table.label,
                "is_query_based": table.is_query_based or 0,
            }
        )

    doc.label = table.label
    if force:
        doc.columns = []
        doc.table_links = []

    for table_link in table.table_links or []:
        if not doc.get("table_links", table_link):
            doc.append("table_links", table_link)

    column_added = False
    for column in table.columns or []:
        # do not overwrite existing columns, since type or label might have been changed
        if any(doc_column.column == column.column for doc_column in doc.columns):
            continue
        doc.append("columns", column)
        column_added = True

    column_removed = False
    column_names = [c.column for c in table.columns]
    for column in doc.columns:
        if column.column not in column_names:
            doc.columns.remove(column)
            column_removed = True

    version = frappe.new_doc("Version")
    # if there's some update to store only then save the doc
    doc_changed = version.update_version_info(doc_before, doc) or column_added or column_removed
    is_new = not exists
    if is_new or doc_changed or force:
        # need to ignore permissions when creating/updating a table in query store
        # a user may have access to create a query and store it, but not to create a table
        doc.save(ignore_permissions=True)
    return doc.name


def parse_sql_tables(sql: str):
    parsed = sqlparse.parse(sql)
    tables = []
    identifier = None
    for statement in parsed:
        for token in statement.tokens:
            is_keyword = token.ttype is sqlparse.tokens.Keyword
            is_from_clause = is_keyword and token.value.lower() == "from"
            is_join_clause = is_keyword and "join" in token.value.lower()
            if is_from_clause or is_join_clause:
                identifier = token.value.lower()
            if identifier and isinstance(token, sqlparse.sql.Identifier):
                tables.append(token.get_real_name())
                identifier = None
            if identifier and isinstance(token, sqlparse.sql.IdentifierList):
                for item in token.get_identifiers():
                    tables.append(item.get_real_name())
                identifier = None

    return [strip_quotes(table) for table in tables]


def get_stored_query_sql(
    sql: str, data_source: Optional[str] = None, dialect: Optional["Dialect"] = None
):
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

    # parse the sql to get the tables
    sql_tables = parse_sql_tables(sql)
    if not sql_tables:
        return None

    # get the sql for the queries
    queries = frappe.get_all(
        "Insights Query",
        filters={
            "name": ("in", set(sql_tables)),
            "data_source": data_source,
        },
        fields=["name", "sql", "data_source", "is_native_query"],
    )
    if not queries:
        return None

    # queries = [
    #     { "name": "QRY-001", "sql": "SELECT name FROM `QRY-004`", "data_source": "Query Store" },
    #     { "name": "QRY-002","sql": "SELECT name FROM `Customer`","data_source": "Demo" },
    #     { "name": "QRY-003","sql": "SELECT name FROM `Supplier`","data_source": "Demo" },
    # ]
    stored_query_sql = {}
    # NOTE: The following works because we don't support multiple data sources in a single query
    quoted = make_wrap_table_fn(dialect=dialect, data_source=data_source)

    for sql in queries:
        if data_source is None:
            data_source = sql.data_source
        if data_source and sql.data_source != data_source:
            frappe.throw("Cannot use queries from different data sources in a single query")

        stored_query_sql[sql.name] = sql.sql
        if not sql.is_native_query:
            # non native queries are already processed and stored in the db
            continue
        sub_stored_query_sql = get_stored_query_sql(sql.sql, data_source, dialect=dialect)
        # sub_stored_query_sql = { 'QRY-004': 'SELECT name FROM `Item`' }
        if not sub_stored_query_sql:
            continue

        cte = "WITH"
        for table, sub_query in sub_stored_query_sql.items():
            cte += f" {quoted(table)} AS ({sub_query}),"
        cte = cte[:-1]
        stored_query_sql[sql.name] = f"{cte} {sql.sql}"

    return stored_query_sql


def make_wrap_table_fn(
    dialect: Optional["Dialect"] = None, data_source: Optional[str] = None
) -> Callable[[str], str]:
    if dialect:
        return dialect.identifier_preparer.quote_identifier
    elif data_source:
        quote = (
            "`"
            if frappe.get_cached_value("Insights Data Source", data_source, "database_type")
            == "MariaDB"
            else '"'
        )
        return lambda table: f"{quote}{table}{quote}"
    return lambda table: table


def process_cte(main_query, data_source=None, dialect=None):
    """
    Replaces stored queries in the main query with the actual query using CTE
    """

    stored_query_sql = get_stored_query_sql(main_query, data_source, dialect=dialect)
    if not stored_query_sql:
        return main_query

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
    quoted = make_wrap_table_fn(dialect=dialect, data_source=data_source)

    for query_name, sql in stored_query_sql.items():
        cte += f" {quoted(query_name)} AS ({sql}),"
    cte = cte[:-1]
    return f"{cte} {main_query}"


def strip_quotes(table):
    if (
        (table.startswith("`") and table.endswith("`"))
        or (table.startswith('"') and table.endswith('"'))
        or (table.startswith("'") and table.endswith("'"))
    ):
        return table[1:-1]
    return table


def add_limit_to_sql(sql, limit=1000):
    stripped_sql = str(sql).strip().rstrip(";")
    return f"WITH limited AS ({stripped_sql}) SELECT * FROM limited LIMIT {limit};"


def replace_query_tables_with_cte(sql, data_source, dialect=None):
    try:
        return process_cte(str(sql).strip().rstrip(";"), data_source=data_source, dialect=dialect)
    except Exception:
        frappe.log_error(title="Failed to process CTE")
        frappe.throw("Failed to replace query tables with CTE")


def compile_query(query, dialect=None):
    compile_args = {"compile_kwargs": {"literal_binds": True}, "dialect": dialect}
    compiled = query.compile(**compile_args)
    return compiled


def execute_and_log(conn, sql, data_source, query_name):
    with Timer() as t:
        try:
            result = conn.exec_driver_sql(sql)
        except Exception as e:
            handle_query_execution_error(e)
    create_execution_log(sql, data_source, t.elapsed, query_name)
    return result


def handle_query_execution_error(e):
    err_lower = str(e).lower()
    if "duplicate column name" in err_lower:
        frappe.throw("Duplicate column name. Please make sure the column labels are unique.")
    if "syntax" in err_lower and "error" in err_lower:
        frappe.throw(
            "Syntax error in the query. Please check the browser console for more details."
        )
    frappe.throw(str(e).split("\n", 1)[0])


def cache_results(sql, data_source, results):
    key = make_digest(sql, data_source)
    frappe.cache().set_value(
        f"insights_query_result:{data_source}:{key}",
        frappe.as_json(results),
        expires_in_sec=60 * 5,
    )


def get_cached_results(sql, data_source):
    key = make_digest(sql, data_source)
    return frappe.parse_json(
        frappe.cache().get_value(f"insights_query_result:{data_source}:{key}")
    )


def create_execution_log(sql, data_source, time_taken=0, query_name=None):
    frappe.get_doc(
        {
            "doctype": "Insights Query Execution Log",
            "data_source": data_source,
            "query": query_name,
            "sql": sqlparse.format(str(sql), reindent=True, keyword_case="upper"),
            "time_taken": time_taken,
        }
    ).insert(ignore_permissions=True)


class Timer:
    # a class to find the time taken to execute a line of code
    # usage:
    # with Timer() as t:
    #     # do something
    # print(t.elapsed)

    def __init__(self):
        self.elapsed = None

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        self.end = time.monotonic()
        self.elapsed = flt(self.end - self.start, 3)
