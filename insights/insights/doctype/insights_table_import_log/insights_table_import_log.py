# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsTableImportLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        batch_size: DF.Int
        data_source: DF.Data
        ended_at: DF.Datetime | None
        memory_limit: DF.Int
        output: DF.LongText | None
        parquet_file: DF.Text | None
        query: DF.Code
        row_limit: DF.Int
        row_size: DF.Float
        rows_imported: DF.Int
        started_at: DF.Datetime | None
        status: DF.Literal["In Progress", "Completed", "Failed"]
        table_name: DF.Data
        time_taken: DF.Int
    # end: auto-generated types

    def log_output(self, message: str, commit: bool = False):
        if not self.output:
            self.output = ""
        self.output += message + "\n\n"
        self.db_update()
        commit and frappe.db.commit()

    @frappe.whitelist()
    def mark_as_failed(self):
        frappe.only_for("System Manager")
        self.status = "Failed"
        self.db_update()
