# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.database.mariadb.database import MariaDBDatabase


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


class SecureMariaDB(MariaDBDatabase):
    def __init__(self, dbName, useSSL, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.useSSL = useSSL
        self.dbName = dbName

    def get_connection_settings(self) -> dict:
        conn_settings = super().get_connection_settings()
        conn_settings["ssl"] = self.useSSL
        conn_settings["ssl_verify_cert"] = self.useSSL

        if self.user != "root":
            # Fix: cannot connect to non-frappe MariaDB instances where database name != user name
            conn_settings["database"] = self.dbName
        return conn_settings

    def sql(self, query, *args, skip_validation=False, **kwargs):
        self.validate_query(query, skip_validation)
        try:
            return super().sql(query, *args, **kwargs)
        except Exception as e:
            frappe.log_error(f"Error fetching data from Secure MariaDB: {e}")
            raise
        finally:
            self.close()

    def validate_query(self, query, skip_validation=False):
        if skip_validation:
            return
        if not query.strip().lower().startswith(("select", "explain", "with", "desc")):
            raise frappe.ValidationError(
                "Only SELECT and EXPLAIN statements are allowed in Query Store"
            )


def create_insights_table(table, force=False):
    exists = frappe.db.exists(
        "Insights Table",
        {
            "data_source": table.data_source,
            "table": table.table,
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
            }
        )

    doc.label = table.label
    doc.columns = []
    if force:
        doc.table_links = []

    for table_link in table.table_links or []:
        if not doc.get("table_links", table_link):
            doc.append("table_links", table_link)

    for column in table.columns or []:
        if not doc.get("columns", column):
            doc.append("columns", column)

    doc.save()
    return doc.name
