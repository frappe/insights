# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _dict
from ibis import _

from .mariadb import get_mariadb_connection
from .postgresql import get_postgres_connection


def get_frappedb_connection(data_source):
    if data_source.database_type == "PostgreSQL":
        return get_postgres_connection(data_source)
    else:
        return get_mariadb_connection(data_source)


def get_primary_data_source():
    data_source = frappe.new_doc("Insights Data Source v3")
    data_source.database_type = "PostgreSQL" if frappe.conf.db_type == "postgres" else "MariaDB"
    data_source.host = frappe.conf.db_host
    data_source.port = frappe.conf.db_port
    data_source.database_name = frappe.conf.db_name
    data_source.username = frappe.conf.db_name
    data_source.password = frappe.conf.db_password
    data_source.use_ssl = False
    return data_source


def get_replica_data_source():
    data_source = get_primary_data_source()

    if frappe.conf.replica_host:
        data_source.host = frappe.conf.replica_host
    if frappe.conf.replica_db_port:
        data_source.port = frappe.conf.replica_db_port
    if frappe.conf.replica_db_name:
        data_source.database_name = frappe.conf.replica_db_name

    if frappe.conf.different_credentials_for_replica:
        data_source.username = (
            frappe.conf.replica_db_user or frappe.conf.replica_db_name or frappe.conf.db_name
        )
        data_source.password = frappe.conf.replica_db_password or frappe.conf.db_password

    return data_source


def get_sitedb_connection():
    # If replica is configured, try replica connection first
    if frappe.conf.read_from_replica:
        try:
            replica = get_replica_data_source()
            return get_frappedb_connection(replica)
        except Exception:
            # If replica fails, fall back to primary
            pass

    primary = get_primary_data_source()
    return get_frappedb_connection(primary)


def is_frappe_db(data_source):
    try:
        db = get_frappedb_connection(data_source)
        db.raw_sql("SET SESSION time_zone='+00:00'")
        db.raw_sql("SET collation_connection = 'utf8mb4_unicode_ci'")
        res = db.raw_sql("SELECT name FROM tabDocType LIMIT 1").fetchall()
        db.con.close()
        return len(res) > 0
    except Exception:
        return False


def get_frappedb_table_links(data_source):
    db = data_source._get_ibis_backend()

    docfield = db.table("tabDocField")
    custom_field = db.table("tabCustom Field")

    standard_links = (
        docfield.select(
            _.fieldname,
            _.fieldtype,
            _.options,
            _.parent,
        )
        .filter((_.fieldtype == "Link") | (_.fieldtype == "Table"))
        .execute()
    )

    custom_links = (
        custom_field.select(
            _.fieldname,
            _.fieldtype,
            _.options,
            _.dt.name("parent"),
        )
        .filter((_.fieldtype == "Link") | (_.fieldtype == "Table"))
        .execute()
    )

    standard_links = standard_links.to_dict(orient="records")
    custom_links = custom_links.to_dict(orient="records")

    all_links = []
    for link_row in standard_links + custom_links:
        link = _dict(link_row)
        if link.fieldtype == "Link":
            all_links.append(
                _dict(
                    {
                        "left_table": link.options,
                        "left_column": "name",
                        "right_table": link.parent,
                        "right_column": link.fieldname,
                    }
                )
            )
        if link.fieldtype == "Table":
            all_links.append(
                _dict(
                    {
                        "left_table": link.parent,
                        "left_column": "name",
                        "right_table": link.options,
                        "right_column": "parent",
                    }
                )
            )

    return all_links
