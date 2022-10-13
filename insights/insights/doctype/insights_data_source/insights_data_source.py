# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from functools import cached_property

import frappe
from frappe import _dict
from frappe.model.document import Document

from .sources.site_db import SiteDB
from .sources.query_store import QueryStore
from .sources.frappe_db import is_frappe_db, FrappeDB

from .sources.models import BaseDataSource
from insights.insights.doctype.insights_query.insights_query import InsightsQuery


SOURCE_TYPES = _dict(
    {
        "RemoteDB": "Database",
        "SiteDB": "Site Database",
        "File": "File",
        "API": "API",
    }
)

SOURCE_STATUS = _dict(
    {
        "Active": "Active",
        "Inactive": "Inactive",
    }
)


class InsightsDataSource(Document):
    @cached_property
    def source(self) -> BaseDataSource:
        return self._get_source()

    def _get_source(self):
        if self.name == "Query Store":
            return QueryStore()

        if self.source_type == SOURCE_TYPES.RemoteDB:
            return self._get_remote_db_source()

        if self.source_type == SOURCE_TYPES.SiteDB:
            return SiteDB()

        frappe.throw(
            f"Unsupported data source type: {self.source_type} and database type: {self.database_type}"
        )

    def _get_remote_db_source(self):
        params = {
            "data_source": self.name,
            "host": self.host,
            "port": self.port,
            "use_ssl": self.use_ssl,
            "username": self.username,
            "password": self.get_password(),
            "database_name": self.database_name,
        }

        if is_frappe_db(params):
            return FrappeDB(**params)

        frappe.throw(f"Unsupported database type: {self.database_type}")

    def validate(self):
        if self.name == "Query Store":
            return
        if self.source_type == SOURCE_TYPES.RemoteDB:
            self._validate_remote_db()
        elif self.source_type == SOURCE_TYPES.SiteDB:
            self._validate_site_db()
        elif self.source_type == SOURCE_TYPES.File:
            self._validate_file()
        elif self.source_type == SOURCE_TYPES.API:
            self._validate_api()

    def _validate_remote_db(self):
        mandatory = ("host", "port", "username", "password", "database_name")
        for field in mandatory:
            if not self.get(field):
                frappe.throw(f"{field} is mandatory for Database")

    def _validate_site_db(self):
        pass

    def _validate_file(self):
        pass

    def _validate_api(self):
        pass

    def on_trash(self):
        if self.name == "Query Store":
            frappe.throw("Cannot delete Query Store")

        # TODO: optimize this
        linked_doctypes = ["Insights Table"]
        for doctype in linked_doctypes:
            for table in frappe.db.get_all(doctype, {"data_source": self.name}):
                frappe.delete_doc(doctype, table.name)

    def before_save(self):
        self._set_status()

    def _set_status(self):
        self.status = (
            SOURCE_STATUS.Active if self.test_connection() else SOURCE_STATUS.Inactive
        )

    def test_connection(self):
        try:
            self.source.connection.test()
            return True
        except BaseException:
            print(f"Test Connection failed for {self.name}")
            return False

    def build_query(self, query: InsightsQuery):
        return self.source.query_builder.build(query)

    def run_query(self, query: InsightsQuery):
        return self.source.query(self.build_query(query))

    def get_running_jobs(self):
        # TODO: implement this
        return []

    def kill_job(self, job_id):
        return

    def get_distinct_column_values(self, *args, **kwargs):
        return self.source.get_distinct_column_values(*args, **kwargs)

    def import_data(self, force=False):
        self.source.import_data(force=force)
