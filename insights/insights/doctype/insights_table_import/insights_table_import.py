# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import csv
import frappe
from frappe import task
from insights.constants import COLUMN_TYPES
from frappe.model.document import Document


class InsightsTableImport(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._filepath = None

    def before_validate(self):
        if not frappe.db.exists("Insights Data Source", {"is_site_db": 1}):
            frappe.throw("Please create a site database data source first")
        self._data_source = frappe.get_doc("Insights Data Source", {"is_site_db": 1})

    def validate(self):
        table_exists = self._data_source.db.conn.sql(
            "SHOW TABLES LIKE %s", self.table_name
        )
        if table_exists and self.if_exists == "Fail":
            frappe.throw("Table already exists. Enter a new different table name")
        if self.source and not self.source.endswith(".csv"):
            frappe.throw("Please attach a CSV file")

    def on_update(self):
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
            return

        self.db_set("status", "Queued")
        import_table.enqueue(
            docname=self.name,
            filepath=self._filepath,
            now=True,  # frappe.flags.in_test or frappe.flags.in_setup_wizard,
        )

    def create_table(self):
        self._data_source = frappe.get_doc("Insights Data Source", {"is_site_db": 1})

        if self.if_exists == "Overwrite":
            self._data_source.db.conn.sql(f"DROP TABLE IF EXISTS `{self.table_name}`")

        # TODO: convert this into pypika query
        pk = "pk bigint primary key"
        column_defs = self.get_column_definitions()
        query = f"""CREATE TABLE `{self.table_name}` ({pk}, {column_defs})
                ENGINE="InnoDB"
                ROW_FORMAT=DYNAMIC
                CHARACTER SET=utf8mb4
                COLLATE=utf8mb4_unicode_ci"""
        self._data_source.db.conn.sql(query)
        self.db_set("status", "Partial Success")

    def get_column_definitions(self):
        column_defs = []
        for row in self.columns:
            column_def = self.get_column_def(row)
            column_defs.append(column_def)
        return ", ".join(column_defs)

    def get_column_def(self, row):
        return make_column_def(row.column, row.type)

    def import_records(self):
        with open(self._filepath, "r") as f:
            column_labels = [d.label for d in self.columns]
            column_names = [d.column for d in self.columns]
            reader = csv.DictReader(f)
            values = []
            for idx, row in enumerate(reader):
                values.append([idx + 1] + [row.get(column) for column in column_labels])
                if len(values) == 10000 or idx == self.rows - 1:
                    self.insert_rows(values, list(["pk"] + column_names))
                    values = []

    def insert_rows(self, values, column_names):
        # values = [[1, "a", "b"], [2, "c", "d"]]
        # column_names = ["name", "column1", "column2"]
        column_name_str = ",".join(
            [f"`{c}`" for c in column_names]
        )  # "`name`,`column1`,`column2`"
        values_str = ",".join(["%s"] * len(values[0]))  # %s,%s,%s
        values_str = ",".join(
            [f"({values_str})"] * len(values)
        )  # (%s,%s,%s),(%s,%s,%s)
        values = [cell or None for row in values for cell in row]
        query = f"""INSERT INTO `{self.table_name}` ({column_name_str}) VALUES {values_str}"""
        self._data_source.db.conn.sql(query, values)


@task(queue="short")
def import_table(docname, filepath=None):
    doc: InsightsTableImport = frappe.get_doc("Insights Table Import", docname)
    doc._filepath = filepath or doc._filepath

    doc.db_set("status", "Started")
    try:
        doc.create_table()
        doc.import_records()
        doc.db_set("status", "Success")
        doc._data_source.db.conn.commit()
        doc._data_source.sync_tables(tables=[doc.table_name])
    except BaseException:
        doc._data_source.db.conn.rollback()
        frappe.log_error(title=f"Failed to import table - {doc.table_name}")
        doc.db_set("status", "Failed")
        doc.db_set("error", "Failed to import table. Check error log for details")


def make_column_def(column, type):
    if not column or not type:
        frappe.throw("Column name and type are required")

    d = COLUMN_TYPES.get(type)
    column_type = f"{d[0]}({d[1]})" if d[1] else d[0]
    return f"`{column}` {column_type}"
