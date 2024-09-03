# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from contextlib import suppress

import frappe
from frappe.model.document import Document


class InsightsTablev3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from insights.insights.doctype.insights_table_column.insights_table_column import (
            InsightsTableColumn,
        )

        columns: DF.Table[InsightsTableColumn]
        data_source: DF.Link
        label: DF.Data
        last_synced_on: DF.Datetime | None
        name: DF.Int | None
        table: DF.Data
    # end: auto-generated types

    def before_insert(self):
        if self.is_duplicate():
            raise frappe.DuplicateEntryError

    def is_duplicate(self):
        return frappe.db.exists(
            "Insights Table v3",
            {
                "data_source": self.data_source,
                "table": self.table,
            },
        )

    @staticmethod
    def create(data_source, table_name):
        doc = frappe.new_doc("Insights Table v3")
        doc.data_source = data_source
        doc.table = table_name
        doc.label = table_name
        with suppress(frappe.DuplicateEntryError):
            doc.save(ignore_permissions=True)
