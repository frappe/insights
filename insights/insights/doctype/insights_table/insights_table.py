# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsTable(Document):
    def on_update(self):
        self.update_columns()
        # clear cache
        frappe.cache().hdel(
            "insights",
            "get_tables_" + self.data_source,
        )
        frappe.cache().hdel(
            "insights",
            "get_all_tables_" + self.data_source,
        )

    def preview(self, limit=20):
        return frappe.get_doc(
            "Insights Data Source", self.data_source
        ).source.describe_table(self.table, limit)

    def get_columns(self):
        if not self.columns:
            self.update_columns()
        return self.columns

    def update_columns(self):
        if self.data_source == "Query Store":
            return

        data_source = frappe.get_doc("Insights Data Source", self.data_source)
        columns = data_source.source.data_importer.get_columns(self.table)
        self.columns = []
        for column in columns:
            self.append(
                "columns",
                {
                    "column": column.get("column"),
                    "label": column.get("label"),
                    "type": column.get("type"),
                },
            )
