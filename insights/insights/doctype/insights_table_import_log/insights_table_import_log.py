# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
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
        parquet_file: DF.Data | None
        query: DF.Code
        row_limit: DF.Int
        row_size: DF.Float
        rows_imported: DF.Int
        started_at: DF.Datetime | None
        table_name: DF.Data
        time_taken: DF.Int
    # end: auto-generated types

    def append_message(self, message: str):
        if not self.output:
            self.output = ""
        self.output += message + "\n\n"
