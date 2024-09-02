# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import ibis
from frappe import _dict
from ibis import _


def get_frappedb_connection_string(data_source):
    password = data_source.get_password(raise_exception=False)
    connection_string = (
        f"mysql://{data_source.username}:{password}"
        f"@{data_source.host}:{data_source.port}/{data_source.database_name}"
    )
    extra_args = frappe._dict(
        ssl=data_source.use_ssl,
        ssl_verify_cert=data_source.use_ssl,
        charset="utf8mb4",
        use_unicode=True,
    )
    return connection_string, extra_args


def get_sitedb_connection_string():
    username = frappe.conf.db_name
    password = frappe.conf.db_password
    database = frappe.conf.db_name
    host = frappe.conf.db_host or "127.0.0.1"
    port = frappe.conf.db_port or "3306"
    connection_string = f"mysql://{username}:{password}@{host}:{port}/{database}"
    extra_args = frappe._dict(
        ssl=False,
        ssl_verify_cert=False,
        charset="utf8mb4",
        use_unicode=True,
    )
    return connection_string, extra_args


def is_frappe_db(data_source):
    connection_string, extra_args = get_frappedb_connection_string(data_source)
    try:
        db = ibis.connect(connection_string, **extra_args)
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
