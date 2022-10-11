# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _dict
from frappe.model.document import Document

from insights.insights.doctype.insights_data_source.connectors.remote_db import (
    RemoteMariaDB,
    RemoteFrappeDB,
)
from insights.insights.doctype.insights_data_source.connectors.local_db import (
    AppDB,
    QueryStore,
)


SOURCE_TYPES = _dict(
    {
        "RemoteDB": "Remote Database",
        "AppDB": "Application Database",
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def connector(self):
        return self.get_connector()

    def get_connector(self):
        if self.is_new() or not self.name:
            return None

        if self.name == "Query Store":
            return QueryStore(self)

        if not self.source_type:
            return None

        if (
            self.source_type == SOURCE_TYPES.RemoteDB
            and self.database_type == "MariaDB"
            and self.check_if_frappe_db()
        ):
            return RemoteFrappeDB(self)

        if (
            self.source_type == SOURCE_TYPES.RemoteDB
            and self.database_type == "MariaDB"
        ):
            return RemoteMariaDB(self)

        if self.source_type == SOURCE_TYPES.AppDB:
            return AppDB()

        frappe.throw(
            f"Unsupported data source type: {self.source_type} and database type: {self.database_type}"
        )

    def set_status(self):
        if not self.connector:
            return

        self.status = (
            SOURCE_STATUS.Active
            if self.connector.test_connection()
            else SOURCE_STATUS.Inactive
        )

    def check_if_frappe_db(self):
        # check if table `tabDocType` exists in the database
        return RemoteMariaDB(self).get_data(
            "select * from information_schema.tables where table_name = 'tabDocType'"
        )

    def before_save(self):
        self.set_status()

    def on_trash(self):
        if self.is_query_store:
            frappe.throw("Cannot delete Query Store")

        # TODO: optimize this
        linked_doctypes = ["Insights Table"]
        for doctype in linked_doctypes:
            for table in frappe.db.get_all(doctype, {"data_source": self.name}):
                frappe.delete_doc(doctype, table.name)
