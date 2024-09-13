# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os

from frappe.utils import get_files_path


def get_duckdb_connection_string(data_source):
    database_path = get_files_path(is_private=1)
    database_path = os.path.join(database_path, f"{data_source.database_name}.duckdb")
    database_path = os.path.abspath(database_path)
    database_path = database_path.lstrip("/")
    return f"duckdb:///{database_path}"
