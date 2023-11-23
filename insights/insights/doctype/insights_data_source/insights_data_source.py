# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from contextlib import suppress
from functools import cached_property, lru_cache

import frappe
from frappe import task
from frappe.model.document import Document
from frappe.utils.caching import redis_cache

from insights import notify
from insights.api.telemetry import track
from insights.insights.doctype.insights_query.insights_query import InsightsQuery
from insights.insights.doctype.insights_team.insights_team import (
    check_table_permission,
    get_permission_filter,
)

from .sources.base_database import BaseDatabase, DatabaseConnectionError
from .sources.frappe_db import FrappeDB, SiteDB, is_frappe_db
from .sources.mariadb import MariaDB
from .sources.postgresql import PostgresDatabase
from .sources.query_store import QueryStore
from .sources.sqlite import SQLiteDB

SOURCE_STATUS = frappe._dict(
    {
        "Active": "Active",
        "Inactive": "Inactive",
    }
)


class InsightsDataSource(Document):
    def before_insert(self):
        if self.is_site_db and frappe.db.exists("Insights Data Source", {"is_site_db": 1}):
            frappe.throw("Only one site database can be configured")

    @frappe.whitelist()
    @redis_cache(ttl=60 * 60 * 24)
    def get_tables(self):
        return frappe.get_list(
            "Insights Table",
            filters={
                "data_source": self.name,
                **get_permission_filter("Insights Table"),
            },
            fields=[
                "name",
                "table",
                "label",
                "hidden",
                "is_query_based",
                "data_source",
            ],
            order_by="hidden asc, label asc",
        )

    @frappe.whitelist()
    def get_queries(self):
        return frappe.get_list(
            "Insights Query",
            filters={
                "data_source": self.name,
                **get_permission_filter("Insights Query"),
            },
            fields=[
                "name",
                "title",
                "data_source",
            ],
        )

    def on_trash(self):
        if self.is_site_db:
            frappe.throw("Cannot delete the site database. It is needed for Insights.")
        if self.name == "Query Store":
            frappe.throw("Cannot delete the Query Store. It is needed for Insights.")

        linked_doctypes = ["Insights Table"]
        for doctype in linked_doctypes:
            for name in frappe.db.get_all(doctype, {"data_source": self.name}, pluck="name"):
                frappe.delete_doc(doctype, name)

        track("delete_data_source")

    @cached_property
    def _db(self) -> BaseDatabase:
        if self.is_site_db:
            return SiteDB(data_source=self.name)
        if self.name == "Query Store":
            return QueryStore()
        if self.database_type == "SQLite":
            return SQLiteDB(data_source=self.name, database_name=self.database_name)

        password = None
        with suppress(BaseException):
            password = self.get_password()

        conn_args = {
            "data_source": self.name,
            "host": self.host,
            "port": self.port,
            "use_ssl": self.use_ssl,
            "username": self.username,
            "password": password,
            "database_name": self.database_name,
            "connection_string": self.connection_string,
        }

        if is_frappe_db(conn_args):
            return FrappeDB(**conn_args)

        if self.database_type == "MariaDB":
            return MariaDB(**conn_args)

        if self.database_type == "PostgreSQL":
            return PostgresDatabase(**conn_args)

        frappe.throw(f"Unsupported database type: {self.database_type}")

    def validate(self):
        if self.is_site_db or self.name == "Query Store":
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

    def before_save(self):
        self.status = SOURCE_STATUS.Active if self.test_connection() else SOURCE_STATUS.Inactive

    def test_connection(self, raise_exception=False):
        try:
            return self._db.test_connection()
        except DatabaseConnectionError:
            return False
        except Exception as e:
            frappe.log_error("Testing Data Source connection failed", e)
            if raise_exception:
                raise e

    def build_query(self, query: InsightsQuery):
        return self._db.build_query(query)

    def run_query(self, query: InsightsQuery):
        try:
            return self._db.run_query(query)
        except Exception as e:
            frappe.log_error("Running query failed")
            notify(
                **{
                    "type": "error",
                    "title": "Failed to run query",
                    "message": str(e),
                }
            )
            raise

    def execute_query(self, query: str, **kwargs):
        return self._db.execute_query(query, **kwargs)

    @task(queue="short")
    def sync_tables(self, *args, **kwargs):
        return self._db.sync_tables(*args, **kwargs)

    @frappe.whitelist()
    def enqueue_sync_tables(self):
        from frappe.utils.scheduler import is_scheduler_inactive

        if is_scheduler_inactive():
            notify(
                **{
                    "title": "Error",
                    "message": "Scheduler is inactive",
                    "type": "error",
                }
            )

        frappe.enqueue(
            _sync_data_source,
            data_source=self.name,
            job_name="sync_data_source",
            queue="long",
            timeout=3600,
            now=True,
        )

    def get_table_columns(self, table):
        return self._db.get_table_columns(table)

    def get_column_options(self, table, column, search_text=None, limit=50):
        return self._db.get_column_options(table, column, search_text, limit)

    def get_table_preview(self, table, limit=100):
        return self._db.get_table_preview(table, limit)

    def get_schema(self):
        return get_data_source_schema(self.name)

    @frappe.whitelist()
    def update_table_link(self, data):
        data = frappe._dict(data)
        data_source = self.name
        check_table_permission(data_source, data.primary_table)

        update_table_link(
            data_source,
            primary_table=data.primary_table,
            foreign_table=data.foreign_table,
            primary_column=data.primary_column,
            foreign_column=data.foreign_column,
            cardinality=data.cardinality,
        )

    @frappe.whitelist()
    def delete_table_link(self, data):
        data = frappe._dict(data)
        data_source = self.name
        check_table_permission(data_source, data.primary_table)

        delete_table_link(
            data_source,
            primary_table=data.primary_table,
            foreign_table=data.foreign_table,
            primary_column=data.primary_column,
            foreign_column=data.foreign_column,
        )


def update_table_link(
    data_source,
    primary_table,
    foreign_table,
    primary_column,
    foreign_column,
    cardinality,
):
    check_table_permission(data_source, primary_table)
    doc = frappe.get_doc(
        "Insights Table",
        {
            "data_source": data_source,
            "table": primary_table,
        },
    )

    link = {
        "primary_key": primary_column,
        "foreign_key": foreign_column,
        "foreign_table": foreign_table,
    }
    existing_link = doc.get("table_links", link)
    if not existing_link:
        link["cardinality"] = cardinality
        doc.append("table_links", link)
        doc.save()
    elif existing_link[0].cardinality != cardinality:
        existing_link[0].cardinality = cardinality
        doc.save()


def delete_table_link(
    data_source,
    primary_table,
    foreign_table,
    primary_column,
    foreign_column,
):
    check_table_permission(data_source, primary_table)
    doc = frappe.get_doc(
        "Insights Table",
        {
            "data_source": data_source,
            "table": primary_table,
        },
    )
    for link in doc.table_links:
        if (
            link.primary_key == primary_column
            and link.foreign_key == foreign_column
            and link.foreign_table == foreign_table
        ):
            doc.remove(link)
            doc.save()
            break


@lru_cache(maxsize=128)
def get_data_source_schema(data_source):
    Table = frappe.qb.DocType("Insights Table")
    TableColumn = frappe.qb.DocType("Insights Table Column")
    schema_list = (
        frappe.qb.from_(Table)
        .select(
            Table.table,
            Table.label,
            Table.is_query_based,
            TableColumn.column,
            TableColumn.label,
            TableColumn.type,
        )
        .left_join(TableColumn)
        .on(Table.name == TableColumn.parent)
        .where((Table.data_source == data_source) & (Table.hidden == 0))
        .run(as_dict=True)
    )
    schema = {}
    for table in schema_list:
        schema.setdefault(
            table.table,
            {
                "label": table.label,
                "is_query_based": table.is_query_based,
                "columns": [],
            },
        )
        schema[table.table]["columns"].append(
            {
                "column": table.column,
                "label": table.label,
                "type": table.type,
            }
        )
    return schema


def _sync_data_source(data_source):
    notify(
        **{
            "title": "Info",
            "message": "Syncing Data Source",
            "type": "info",
        }
    )
    source = frappe.get_doc("Insights Data Source", data_source)
    source.sync_tables()
    notify(
        **{
            "title": "Success",
            "message": "Data Source Synced",
            "type": "success",
        }
    )
