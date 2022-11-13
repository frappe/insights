# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import csv
import frappe
from frappe import task
from functools import cached_property
from frappe.model.document import Document


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
        if (
            self._data_source.db.table_exists(self.table_name)
            and self.if_exists == "Fail"
        ):
            frappe.throw("Table already exists. Enter a new different table name")

    def before_save(self):
        if not self._filepath and frappe.db.exists("File", {"file_url": self.source}):
            file = frappe.get_doc("File", {"file_url": self.source})
            self._filepath = file.get_full_path()

        if not self._filepath or not os.path.exists(self._filepath):
            return

        column_names = []
        with open(self._filepath, "r") as f:
            # read only the first line to get the column names
            reader = csv.reader(f)
            column_names = next(reader)
            no_of_rows = sum(1 for _ in reader)

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
        self.start_import.enqueue(
            self=self,
            now=frappe.flags.in_test
            or frappe.flags.in_setup_wizard
            or frappe.flags.in_migrate,
        )

    @task(queue="long")
    def start_import(self, filepath=None):
        self._filepath = filepath or self._filepath
        self.db_set("status", "Started")
        try:
            self._data_source.db.import_table(self)
            self.db_set("status", "Success")
        except BaseException as e:
            print(f"Error importing table {self.table_name}", e)
            frappe.log_error(
                title=f"Insights: Failed to import table - {self.table_name}"
            )
            self.db_set("status", "Failed")
            self.db_set("error", "Failed to import table. Check error log for details")
