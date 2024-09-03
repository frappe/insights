# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os

import frappe
import pandas as pd
from frappe.utils import get_files_path

from insights.utils import detect_encoding

from ...insights_table_import.insights_table_import import InsightsTableImport


def import_table(self, import_doc: InsightsTableImport):
    encoding = detect_encoding(import_doc._filepath)
    df = pd.read_csv(import_doc._filepath, encoding=encoding)

    df.columns = [frappe.scrub(c) for c in df.columns]
    columns_to_import = [c.column for c in import_doc.columns]

    df = df[columns_to_import]
    table = import_doc.table_name
    df.to_sql(
        name=table,
        con=self.engine,
        index=False,
        if_exists="replace",
    )
    # create_insights_table()


def get_sqlite_connection_string(data_source):
    database_path = get_files_path(is_private=1)
    database_path = os.path.join(database_path, f"{data_source.database_name}.sqlite")
    database_path = os.path.abspath(database_path)
    database_path = database_path.lstrip("/")
    return f"sqlite:///{database_path}"
