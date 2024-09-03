# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re

import frappe
import ibis
from frappe.model.document import Document
from frappe.utils.caching import site_cache
from ibis import BaseBackend

from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    WAREHOUSE_DB_NAME,
)
from insights.insights.doctype.insights_table_column.insights_table_column import (
    InsightsTableColumn,
)
from insights.insights.doctype.insights_table_link_v3.insights_table_link_v3 import (
    InsightsTableLinkv3,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    InsightsTablev3,
)

from .connectors.duckdb import get_duckdb_connection_string
from .connectors.frappe_db import (
    get_frappedb_connection_string,
    get_frappedb_table_links,
    get_sitedb_connection_string,
    is_frappe_db,
)
from .connectors.mariadb import get_mariadb_connection_string
from .connectors.postgresql import get_postgres_connection_string
from .connectors.sqlite import get_sqlite_connection_string


class InsightsDataSourceDocument:
    def autoname(self):
        self.name = frappe.scrub(self.title)

    def before_insert(self):
        if self.name == WAREHOUSE_DB_NAME:
            frappe.throw("Cannot create a Data Source with this name")

        if self.is_site_db and frappe.db.exists(
            "Insights Data Source v3", {"is_site_db": 1}
        ):
            frappe.throw("Only one site database can be configured")

    def on_update(self: "InsightsDataSourcev3"):
        if self.is_site_db and not self.is_frappe_db:
            self.db_set("is_frappe_db", 1)

        credentials_changed = self.has_credentials_changed()
        if (
            not self.is_site_db
            and credentials_changed
            and self.database_type in ["MariaDB", "PostgreSQL"]
        ):
            self.db_set("is_frappe_db", is_frappe_db(self))

        self.status = "Active" if self.test_connection() else "Inactive"
        self.db_set("status", self.status)

        if self.status == "Active" and credentials_changed:
            self.update_table_list()

    def has_credentials_changed(self):
        doc_before = self.get_doc_before_save()
        if not doc_before:
            return True
        return (
            self.database_name != doc_before.database_name
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


class InsightsDataSourcev3(InsightsDataSourceDocument, Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        connection_string: DF.Text | None
        database_name: DF.Data | None
        database_type: DF.Literal["MariaDB", "PostgreSQL", "SQLite", "DuckDB"]
        host: DF.Data | None
        is_frappe_db: DF.Check
        is_site_db: DF.Check
        password: DF.Password | None
        port: DF.Int
        status: DF.Literal["Inactive", "Active"]
        title: DF.Data
        use_ssl: DF.Check
        username: DF.Data | None
    # end: auto-generated types

    def _get_ibis_backend(self) -> BaseBackend:
        if self.name in frappe.local.insights_db_connections:
            return frappe.local.insights_db_connections[self.name]

        connection_string = self.get_connection_string()
        db: BaseBackend = ibis.connect(connection_string)
        print(f"Connected to {self.name} ({self.title})")

        if self.is_frappe_db:
            db.raw_sql("SET SESSION time_zone='+00:00'")
            db.raw_sql("SET collation_connection = 'utf8mb4_unicode_ci'")

        frappe.local.insights_db_connections[self.name] = db
        return db

    def get_connection_string(self):
        if self.is_site_db:
            return get_sitedb_connection_string()
        if self.database_type == "SQLite":
            return get_sqlite_connection_string(self)
        if self.database_type == "DuckDB":
            return get_duckdb_connection_string(self)
        if self.is_frappe_db:
            return get_frappedb_connection_string(self)
        if self.database_type == "MariaDB":
            return get_mariadb_connection_string(self)
        if self.database_type == "PostgreSQL":
            return get_postgres_connection_string(self)

        frappe.throw(f"Unsupported database type: {self.database_type}")

    def test_connection(self, raise_exception=False):
        try:
            db = self._get_ibis_backend()
            res = db.raw_sql("SELECT 1").fetchall()
            return res[0][0] == 1
        except Exception as e:
            frappe.log_error("Testing Data Source connection failed", e)
            if raise_exception:
                raise e

    @frappe.whitelist()
    def update_table_list(self):
        blacklist_patterns = ["^_", "^sqlite_"]
        blacklisted = lambda table: any(re.match(p, table) for p in blacklist_patterns)
        remote_db = self._get_ibis_backend()
        tables = remote_db.list_tables()
        tables = [t for t in tables if not blacklisted(t)]

        if not tables or len(tables) == frappe.db.count(
            "Insights Table v3",
            {"data_source": self.name},
        ):
            return

        errors = []
        for table in tables:
            try:
                InsightsTablev3.create(self.name, table)
            except Exception as e:
                errors.append(f"Error syncing {table}: {e}")

        if errors:
            frappe.throw("\n".join(errors))

        self.update_table_links()

    def update_table_links(self):
        links = []
        if self.is_site_db or self.is_frappe_db:
            links = get_frappedb_table_links(self)

        for link in links:
            InsightsTableLinkv3.create(
                self.name,
                link.left_table,
                link.right_table,
                link.left_column,
                link.right_column,
            )


@frappe.whitelist()
def get_data_sources():
    return frappe.get_all(
        "Insights Data Source v3",
        filters={"status": "Active"},
        fields=[
            "name",
            "status",
            "title",
            "owner",
            "creation",
            "modified",
            "database_type",
        ],
    )


@frappe.whitelist()
def get_data_source_tables(data_source=None, search_term=None, limit=100):
    tables = frappe.get_all(
        "Insights Table v3",
        filters={
            "data_source": data_source or ["is", "set"],
        },
        or_filters={
            "label": ["is", "set"] if not search_term else ["like", f"%{search_term}%"],
            "table": ["is", "set"] if not search_term else ["like", f"%{search_term}%"],
        },
        fields=["name", "table", "label", "data_source", "last_synced_on"],
        limit=limit,
    )

    ret = []
    for table in tables:
        ret.append(
            frappe._dict(
                {
                    "label": table.label,
                    "table_name": table.table,
                    "data_source": table.data_source,
                    "last_synced_on": table.last_synced_on,
                }
            )
        )
    return ret


@frappe.whitelist()
@site_cache
def get_table_columns(data_source, table_name):
    ds = frappe.get_doc("Insights Data Source v3", data_source)
    db = ds._get_ibis_backend()
    table = db.table(table_name)
    return InsightsTableColumn.from_ibis_schema(table.schema())


@frappe.whitelist()
def update_data_source_tables(data_source):
    ds = frappe.get_doc("Insights Data Source v3", data_source)
    ds.update_table_list()


@frappe.whitelist()
def get_table_links(data_source, left_table, right_table):
    return InsightsTableLinkv3.get_links(data_source, left_table, right_table)


def make_data_source(data_source):
    data_source = frappe._dict(data_source)
    ds = frappe.new_doc("Insights Data Source v3")
    ds.database_type = data_source.database_type
    ds.title = data_source.title
    ds.host = data_source.host
    ds.port = data_source.port
    ds.username = data_source.username
    ds.password = data_source.password
    ds.database_name = data_source.database_name
    ds.use_ssl = data_source.use_ssl
    ds.connection_string = data_source.connection_string
    return ds


@frappe.whitelist()
def test_connection(data_source):
    ds = make_data_source(data_source)
    return ds.test_connection(raise_exception=True)


@frappe.whitelist()
def create_data_source(data_source):
    ds = make_data_source(data_source)
    ds.save()
    return ds.name


def before_request():
    if not hasattr(frappe.local, "insights_db_connections"):
        frappe.local.insights_db_connections = {}


def after_request():
    for db in frappe.local.insights_db_connections.values():
        db.disconnect()
