# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import csv
import os
from functools import cached_property

import frappe
from frappe import task
from frappe.model.document import Document

from insights.utils import detect_encoding


class InsightsTableImport(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._filepath = None

    @cached_property
    def _data_source(self):
        return frappe.get_doc("Insights Data Source", self.data_source)

    def validate(self):
        if not self._data_source.allow_imports:
            frappe.throw("Data source does not allow imports")
        if self.source and not self.source.endswith(".csv"):
            frappe.throw("Please attach a CSV file")
        if self._data_source._db.table_exists(self.table_name) and self.if_exists == "Fail":
            frappe.throw("Table already exists. Enter a new different table name")

    def before_save(self):
        if not self._filepath and frappe.db.exists("File", {"file_url": self.source}):
            file = frappe.get_doc("File", {"file_url": self.source})
            self._filepath = file.get_full_path()

        if not self._filepath or not os.path.exists(self._filepath):
            return

        if self.is_new():
            self.set_columns_and_no_of_rows()

    def set_columns_and_no_of_rows(self):
        encoding = detect_encoding(self._filepath)
        with open(self._filepath, "r", encoding=encoding, errors="replace") as f:
            # read only the first line to get the column names
            csv_reader = csv.DictReader(f)
            column_names = csv_reader.fieldnames
            rows = list(csv_reader)
            no_of_rows = len(rows)

        self.db_set("rows", no_of_rows)
        for column in column_names:
            if not self.get("columns", {"column": frappe.scrub(column)}):
                self.append(
                    "columns",
                    {
                        "type": "String",
                        "column": frappe.scrub(column),
                        "label": frappe.unscrub(column),
                    },
                )

    def on_submit(self):
        if not self._filepath:
            self.db_set("status", "Failed")
            self.db_set("error", "Attached file not found")
            print("Attached file not found")
            return

        self.db_set("status", "Queued")
        self.start_import.enqueue(name=self.name, filepath=self._filepath, now=True)

    @staticmethod
    @task(queue="long")
    def start_import(name, filepath=None):
        table_import = frappe.get_doc("Insights Table Import", name)
        table_import._filepath = filepath or table_import._filepath
        table_import.db_set("status", "Started")

        try:
            table_import._data_source._db.import_table(table_import)
            table_import.db_set("status", "Success")
        except Exception as e:
            print(f"Error importing table {table_import.table_name}", e)
            frappe.log_error(title=f"Insights: Failed to import table - {table_import.table_name}")
            table_import.db_set("status", "Failed")
            table_import.db_set("error", "Failed to import table. Check error log for details")
