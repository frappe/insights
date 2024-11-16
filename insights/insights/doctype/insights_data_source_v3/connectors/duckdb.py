# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os

import ibis
from frappe.utils import get_files_path


def get_duckdb_connection(data_source, read_only=True):
    path = os.path.realpath(get_files_path(is_private=1))
    path = os.path.join(path, f"{data_source.database_name}.duckdb")
    return ibis.duckdb.connect(path, read_only=read_only)
