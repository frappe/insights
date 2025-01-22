# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsChartv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        chart_type: DF.Data | None
        config: DF.JSON | None
        data_query: DF.Link | None
        is_public: DF.Check
        old_name: DF.Data | None
        operations: DF.JSON | None
        query: DF.Link | None
        title: DF.Data | None
        use_live_connection: DF.Check
        workbook: DF.Link | None
    # end: auto-generated types

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.config, dict):
            self.config = frappe.as_json(self.config)
        if isinstance(self.operations, list):
            self.operations = frappe.as_json(self.operations)
        return super().get_valid_dict(*args, **kwargs)

    def before_save(self):
        self.set_data_query()

    def on_trash(self):
        frappe.db.delete("Insights Query v3", self.data_query)

    def set_data_query(self):
        if self.data_query:
            return
        doc = frappe.new_doc("Insights Query v3").insert()
        self.db_set("data_query", doc.name)
