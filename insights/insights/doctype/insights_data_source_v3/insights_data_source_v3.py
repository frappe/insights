# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re
from collections.abc import Generator
from contextlib import contextmanager

import frappe
import ibis
from frappe.model.document import Document
from frappe.utils.caching import site_cache
from ibis import BaseBackend

from insights.api.telemetry import track
from insights.insights.doctype.insights_table_column.insights_table_column import (
    InsightsTableColumn,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    sync_insights_table,
)

from .connectors.frappe_db import (
    get_frappedb_connection_string,
    get_sitedb_connection_string,
    is_frappe_db,
)
from .connectors.mariadb import get_mariadb_connection_string
from .connectors.postgresql import get_postgres_connection_string
from .connectors.sqlite import get_sqlite_connection_string
from .data_warehouse import DataWarehouse


class InsightsDataSourceDocument:
    def autoname(self):
        self.name = frappe.scrub(self.title)

    def before_insert(self):
        if self.is_site_db and frappe.db.exists(
            "Insights Data Source v3", {"is_site_db": 1}
        ):
            frappe.throw("Only one site database can be configured")

    def before_save(self: "InsightsDataSourcev3"):
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
        )

    def on_trash(self):
        if self.is_site_db:
            frappe.throw("Cannot delete the site database. It is needed for Insights.")

        linked_doctypes = ["Insights Table v3"]
        for doctype in linked_doctypes:
            for name in frappe.db.get_all(
                doctype, {"data_source": self.name}, pluck="name"
            ):
                frappe.delete_doc(doctype, name)

        track("delete_data_source")

    def validate(self):
        if self.is_site_db:
            return
        if self.database_type == "SQLite":
            self.validate_sqlite_fields()
        else:
            self.validate_remote_db_fields()

    def validate_sqlite_fields(self):
        mandatory = ("database_name",)
        for field in mandatory:
            if not self.get(field):
                frappe.throw(f"{field} is mandatory for SQLite")

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
        database_type: DF.Literal["MariaDB", "PostgreSQL", "SQLite"]
        host: DF.Data | None
        is_frappe_db: DF.Check
        is_site_db: DF.Check
        password: DF.Password | None
        port: DF.Int
        status: DF.Literal["Inactive", "Active"]
        tables: DF.JSON | None
        title: DF.Data
        use_ssl: DF.Check
        username: DF.Data | None
    # end: auto-generated types

    @contextmanager
    def _get_ibis_backend(self) -> Generator[BaseBackend, None, None]:
        connection_string, extra_args = self.get_connection_string()
        db: BaseBackend = ibis.connect(connection_string, **extra_args)

        if self.is_frappe_db:
            db.raw_sql("SET SESSION time_zone='+00:00'")
            db.raw_sql("SET collation_connection = 'utf8mb4_unicode_ci'")

        try:
            yield db
        finally:
            db.con.close()

    def get_connection_string(self):
        if self.is_site_db:
            return get_sitedb_connection_string()
        if self.database_type == "SQLite":
            return get_sqlite_connection_string(self)
        if self.is_frappe_db:
            return get_frappedb_connection_string(self)
        if self.database_type == "MariaDB":
            return get_mariadb_connection_string(self)
        if self.database_type == "PostgreSQL":
            return get_postgres_connection_string(self)

        frappe.throw(f"Unsupported database type: {self.database_type}")

    def test_connection(self, raise_exception=False):
        try:
            with self._get_ibis_backend() as db:
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
        with self._get_ibis_backend() as remote_db:
            tables = remote_db.list_tables()
            tables = [t for t in tables if not blacklisted(t)]
            self.db_set("tables", frappe.as_json(tables))

    @frappe.whitelist()
    def sync_table(self, table_name):
        table = DataWarehouse().get_table(self.name, table_name, sync=True)
        columns = InsightsTableColumn.from_ibis_schema(table.schema())
        sync_insights_table(self.name, table_name, columns=columns)


@frappe.whitelist()
def get_data_sources():
    return frappe.get_all(
        "Insights Data Source v3",
        filters={"status": "Active"},
        fields=["name", "title"],
    )


@frappe.whitelist()
@site_cache
def get_data_source_tables(data_source=None, search_term=None, limit=100):
    tables = []
    for ds in frappe.get_all(
        "Insights Data Source v3",
        filters={
            "status": "Active",
            "name": data_source or ["is", "set"],
        },
        fields=["name", "tables"],
    ):
        if not ds.tables:
            continue
        ds_tables = frappe.parse_json(ds.tables)
        ds_tables = [
            table
            for table in ds_tables
            if not search_term or search_term.lower() in table.lower()
        ]
        tables.extend(
            [
                frappe._dict(
                    {
                        "table_name": table_name,
                        "data_source": ds.name,
                    }
                )
                for table_name in ds_tables
            ]
        )
    return tables[:limit]


@frappe.whitelist()
@site_cache
def get_table_columns(data_source, table_name):
    ds = frappe.get_doc("Insights Data Source v3", data_source)
    with ds._get_ibis_backend() as db:
        table = db.table(table_name)
        return InsightsTableColumn.from_ibis_schema(table.schema())
