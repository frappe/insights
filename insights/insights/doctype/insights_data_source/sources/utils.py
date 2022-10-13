# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint
from .models import Connection, QueryRunner
from frappe.database.mariadb.database import MariaDBDatabase


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


class FrappeSiteConnection(Connection):
    def __init__(self, host, port, username, password, database_name, use_ssl):
        self._connection = SecureMariaDB(
            dbName=database_name,
            user=username,
            password=password,
            host=host,
            port=cint(port),
            useSSL=use_ssl,
        )

    def get(self):
        return self._connection

    def test(self) -> bool:
        try:
            return self._connection.a_row_exists("DocType")
        except Exception as e:
            frappe.log_error(f"Error connecting to Site: {e}")

    def close(self) -> None:
        self._connection.close()


class DatabaseQueryRunner(QueryRunner):
    def __init__(self, connection: Connection):
        self.connection = connection

    def execute(self, query, *args, skip_validation=False, **kwargs):
        self.validate_query(query, skip_validation)
        try:
            return self.connection.get().sql(query, *args, **kwargs)
        except Exception as e:
            frappe.log_error(f"Error fetching data from RemoteDB: {e}")
            raise
        finally:
            self.connection.close()

    def validate_query(self, query, skip_validation=False):
        if skip_validation:
            return
        if not query.strip().lower().startswith(("select", "explain", "with", "desc")):
            raise frappe.ValidationError(
                "Only SELECT and EXPLAIN statements are allowed in Query Store"
            )


def get_site_db_connection():
    return FrappeSiteConnection(
        host=None,
        port=None,
        username=frappe.conf.db_name,
        password=frappe.conf.db_password,
        database_name=frappe.conf.db_name,
        use_ssl=False,
    )
