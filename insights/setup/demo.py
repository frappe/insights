# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import frappe
from frappe.database.db_manager import DbManager
from frappe.installer import extract_sql_gzip
from frappe.database.mariadb.setup_db import get_root_connection


def setup_db():
    db_name, db_user, db_password = (
        "insights_demo",
        "insights_demo",
        "demo_pass",
    )

    if demo_db_exists(db_name):
        return

    # create a new database
    create_database(db_name, db_user, db_password)

    # create a data source for the new database
    data_source = frappe.get_doc(
        {
            "doctype": "Data Source",
            "title": "Demo Database",
            "database_type": "MariaDB",
            "database_name": db_name,
            "username": db_user,
            "password": db_password,
        }
    )
    data_source.insert(ignore_if_duplicate=True)


def demo_db_exists(db_name):
    frappe.local.session = frappe._dict({"user": "Administrator"})

    root_conn = get_root_connection(None, None)
    dbman = DbManager(root_conn)

    db_exists = db_name in dbman.get_database_list()

    root_conn.close()
    return db_exists


def create_database(db_name, db_user, db_password, force=False):
    frappe.local.session = frappe._dict({"user": "Administrator"})

    root_conn = get_root_connection(None, None)
    dbman = DbManager(root_conn)

    if force:
        dbman.delete_user(db_user)
        dbman.drop_database(db_name)

    dbman.create_user(db_user, db_password)
    dbman.create_database(db_name)

    dbman.grant_all_privileges(db_name, db_user)
    dbman.flush_privileges()

    download_demo_db()
    restore_demo_db(db_name, db_user, db_password)

    root_conn.close()


def download_demo_db():
    import requests
    from urllib.parse import urlparse

    url = "https://github.com/frappe/insights/raw/setup-demo/insights/fixtures/insights_demo.sql.gz"

    """Download file locally under sites path and return local path"""
    filename = urlparse(url).path.split("/")[-1]
    local_filename = os.path.join(frappe.get_site_path("private", "files"), filename)

    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    f.write(chunk)
    except Exception as e:
        frappe.log_error(
            "Error downloading demo database. Please check your internet connection."
        )
        raise e


def restore_demo_db(db_name, db_user, db_password):
    sql_path = ""
    try:
        sql_path = extract_sql_gzip(
            frappe.get_site_path("private", "files", "insights_demo.sql.gz")
        )
        DbManager.restore_database(db_name, sql_path, db_user, db_password)

    except Exception as e:
        frappe.log_error(
            "Error restoring insights_demo.sql.gz. Please check if the file exists and is not corrupted."
        )
        raise e
    finally:
        remove_extracted_sql(sql_path)


def remove_extracted_sql(sql_path):
    if os.path.exists(sql_path):
        os.remove(sql_path)
