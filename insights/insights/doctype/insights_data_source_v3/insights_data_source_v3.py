# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re
from contextlib import contextmanager

import frappe
from frappe.model.document import Document
from ibis import BaseBackend

from insights.insights.doctype.insights_table_link_v3.insights_table_link_v3 import (
    InsightsTableLinkv3,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    InsightsTablev3,
)

from .connectors.bigquery import get_bigquery_connection
from .connectors.duckdb import get_duckdb_connection
from .connectors.frappe_db import (
    get_frappedb_connection,
    get_frappedb_table_links,
    get_sitedb_connection,
    is_frappe_db,
)
from .connectors.mariadb import get_mariadb_connection
from .connectors.mssql import get_mssql_connection
from .connectors.postgresql import get_postgres_connection
from .connectors.sqlite import get_sqlite_connection
from .data_warehouse import WAREHOUSE_DB_NAME


class DataSourceConnectionError(frappe.ValidationError):
    pass


class InsightsDataSourceDocument:
    def autoname(self):
        self.name = frappe.scrub(self.title)

    def before_insert(self):
        if self.name == WAREHOUSE_DB_NAME:
            frappe.throw("Cannot create a Data Source with this name")

        if (
            not frappe.flags.in_migrate
            and self.is_site_db
            and frappe.db.exists("Insights Data Source v3", {"is_site_db": 1})
        ):
            frappe.throw("Only one site database can be configured")

    def on_update(self):
        if self.is_site_db:
            self.db_set("is_frappe_db", 1)
            self.db_set("status", "Active")

            if frappe.conf.db_type == "postgres":
                self.db_set("database_type", "PostgreSQL")

            with db_connections():
                self.update_table_list()

            return

        credentials_changed = self.has_credentials_changed()
        if not self.is_site_db and credentials_changed and self.database_type in ["MariaDB", "PostgreSQL"]:
            self.db_set("is_frappe_db", is_frappe_db(self))

        self.status = "Active" if self.test_connection() else "Inactive"
        self.db_set("status", self.status)

        if self.status == "Active" and credentials_changed:
            self.update_table_list()

    def has_credentials_changed(self):
        doc_before = self.get_doc_before_save()
        if not doc_before:
            return True
        if self.database_type in ["SQLite", "DuckDB"]:
            return self.database_name != doc_before.database_name
        elif self.database_type == "BigQuery":
            return (
                self.bigquery_project_id != doc_before.bigquery_project_id
                or self.bigquery_dataset_id != doc_before.bigquery_dataset_id
                or self.bigquery_service_account_key != doc_before.bigquery_service_account_key
            )
        elif self.database_type in ["MariaDB", "PostgreSQL"]:
            return (
                self.database_name != doc_before.database_name
                or self.schema != doc_before.schema
                or self.password != doc_before.password
                or self.username != doc_before.username
                or self.host != doc_before.host
                or self.port != doc_before.port
                or self.use_ssl != doc_before.use_ssl
            )

    def on_trash(self):
        if self.is_site_db:
            frappe.throw("Cannot delete the site database. It is needed for Insights.")

        linked_doctypes = ["Insights Table v3", "Insights Table Link v3"]
        for doctype in linked_doctypes:
            for name in frappe.db.get_all(
                doctype,
                {"data_source": self.name},
                pluck="name",
            ):
                frappe.delete_doc(doctype, name)

    def validate(self):
        if self.is_site_db:
            return
        if self.database_type == "SQLite" or self.database_type == "DuckDB":
            self.validate_database_name()
        elif self.database_type == "BigQuery":
            self.validate_bigquery_fields()
        else:
            self.validate_remote_db_fields()

    def validate_database_name(self):
        mandatory = ("database_name",)
        for field in mandatory:
            if not self.get(field):
                frappe.throw(f"{field} is mandatory for {self.database_type} Database")

    def validate_remote_db_fields(self):
        if self.connection_string:
            return
        mandatory = ("host", "port", "username", "password", "database_name")
        for field in mandatory:
            if not self.get(field):
                frappe.throw(f"{field} is mandatory for Database")

    def validate_bigquery_fields(self):
        mandatory = (
            "bigquery_project_id",
            "bigquery_dataset_id",
            "bigquery_service_account_key",
        )
        for field in mandatory:
            if not self.get(field):
                frappe.throw(f"{field} is mandatory for BigQuery Database")


class InsightsDataSourcev3(InsightsDataSourceDocument, Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        bigquery_dataset_id: DF.Data | None
        bigquery_project_id: DF.Data | None
        bigquery_service_account_key: DF.JSON | None
        connection_string: DF.Text | None
        database_name: DF.Data | None
        database_type: DF.Literal["MariaDB", "PostgreSQL", "SQLite", "DuckDB", "BigQuery"]
        enable_stored_procedure_execution: DF.Check
        host: DF.Data | None
        is_frappe_db: DF.Check
        is_site_db: DF.Check
        password: DF.Password | None
        port: DF.Int
        schema: DF.Data | None
        status: DF.Literal["Inactive", "Active"]
        title: DF.Data
        use_ssl: DF.Check
        username: DF.Data | None
    # end: auto-generated types

    def _get_ibis_backend(self) -> BaseBackend:
        if self.name in frappe.local.insights_db_connections:
            return frappe.local.insights_db_connections[self.name]

        try:
            db: BaseBackend = self._get_db_connection()
        except Exception as e:
            frappe.throw(
                title="Connection Error",
                msg=f"There was an error connecting to '{self.title}' data source: {e!s}",
                exc=DataSourceConnectionError,
            )

        print(f"Connected to {self.name} ({self.title})")

        if self.database_type == "MariaDB":
            db.raw_sql("SET SESSION time_zone='+00:00'")
            db.raw_sql("SET collation_connection = 'utf8mb4_unicode_ci'")
            MAX_STATEMENT_TIMEOUT = (
                frappe.db.get_single_value("Insights Settings", "max_execution_time", cache=True) or 180
            )
            ## Todo: Permanent fix for this
            try:
                db.raw_sql(f"SET MAX_STATEMENT_TIME={MAX_STATEMENT_TIMEOUT}")
            except Exception:
                pass

        frappe.local.insights_db_connections[self.name] = db
        return db

    def _get_db_connection(self) -> BaseBackend:
        if self.is_site_db:
            return get_sitedb_connection()
        if self.is_frappe_db:
            return get_frappedb_connection(self)
        if self.database_type == "MariaDB":
            return get_mariadb_connection(self)
        if self.database_type == "PostgreSQL":
            return get_postgres_connection(self)
        if self.database_type == "DuckDB":
            return get_duckdb_connection(self)
        if self.database_type == "SQLite":
            return get_sqlite_connection(self)
        if self.database_type == "BigQuery":
            return get_bigquery_connection(self)
        if self.database_type == "MSSQL":
            return get_mssql_connection(self)

        frappe.throw(f"Unsupported database type: {self.database_type}")

    def get_table_list(self):
        db = self._get_ibis_backend()

        database_name = self.database_name
        if self.is_site_db:
            database_name = frappe.conf.db_name

        if not database_name or self.database_type == "DuckDB" or self.database_type == "SQLite":
            return db.list_tables()

        if self.database_type == "PostgreSQL":
            schema = self.schema or "public"
            schemas = schema.split(",")
            tables = []
            for schema in schemas:
                schema_tables = db.list_tables(database=(database_name, schema))
                schema_tables = [f"{schema}.{table}" for table in schema_tables]
                tables.extend(schema_tables)
            return tables

        contains_special_chars = re.search(r"[^a-zA-Z0-9_]", database_name)
        if not contains_special_chars:
            return db.list_tables()

        quoted_db_name = f"{db.dialect.QUOTE_START}{database_name}{db.dialect.QUOTE_END}"
        return db.list_tables(database=quoted_db_name)

    def test_connection(self, raise_exception=False):
        try:
            self.get_table_list()
            return True
        except Exception as e:
            if raise_exception:
                raise e

    def update_table_list(self, force=False):
        remote_tables = self.get_table_list()

        blacklist_patterns = ["^_", "^sqlite_"]
        blacklisted = lambda table: any(re.match(p, table) for p in blacklist_patterns)
        remote_tables = [t for t in remote_tables if not blacklisted(t)]

        if not remote_tables:
            return

        if force:
            frappe.db.delete(
                "Insights Table v3",
                {"data_source": self.name},
            )

        tables_to_import = set(remote_tables)
        if not force:
            existing_tables = frappe.get_all(
                "Insights Table v3",
                {"data_source": self.name},
                pluck="table",
            )
            tables_to_import = set(remote_tables) - set(existing_tables)

        if not tables_to_import:
            return

        InsightsTablev3.bulk_create(self.name, list(tables_to_import))
        self.update_table_links(force)

    def update_table_links(self, force=False):
        links = []
        if self.is_site_db or self.is_frappe_db:
            links = get_frappedb_table_links(self)

        if force:
            frappe.db.delete(
                "Insights Table Link v3",
                {"data_source": self.name},
            )

        for link in links:
            InsightsTableLinkv3.create(
                self.name,
                link.left_table,
                link.right_table,
                link.left_column,
                link.right_column,
            )

    def get_ibis_table(self, table_name):
        remote_db = self._get_ibis_backend()
        if self.database_type == "PostgreSQL" and "." in table_name:
            schema, table = table_name.split(".")
            return remote_db.table(table, database=schema)
        return remote_db.table(table_name)


def before_request():
    if not hasattr(frappe.local, "insights_db_connections"):
        frappe.local.insights_db_connections = {}


def after_request():
    closed = {}
    for name, db in getattr(frappe.local, "insights_db_connections", {}).items():
        try:
            db.disconnect()
            closed[name] = True
        except Exception:
            frappe.log_error(title=f"Failed to disconnect db connection for {name}")

    for name in closed:
        del frappe.local.insights_db_connections[name]


@contextmanager
def db_connections():
    before_request()
    try:
        yield
    finally:
        after_request()
