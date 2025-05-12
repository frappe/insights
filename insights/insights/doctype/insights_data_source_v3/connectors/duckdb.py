# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os

import frappe
import ibis
from frappe.utils import get_files_path


def get_duckdb_connection(data_source, read_only=True):
    name = data_source.name or frappe.scrub(data_source.title)
    db_name = data_source.database_name

    if db_name.startswith("http"):
        db = ibis.duckdb.connect()
        db.load_extension("httpfs")
        db.attach(db_name, name, read_only=True)
        db.raw_sql(f"USE {name}")
        return db
    else:
        path = os.path.realpath(get_files_path(is_private=1))
        path = os.path.join(path, f"{db_name}.duckdb")

        if not os.path.exists(path):
            # create the database file if it doesn't exist
            db = ibis.duckdb.connect(path)
            db.disconnect()

        return ibis.duckdb.connect(path, read_only=read_only)
