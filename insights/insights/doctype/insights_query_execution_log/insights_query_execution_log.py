# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsQueryExecutionLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        data_source: DF.Data | None
        query: DF.Data | None
        use_data_store: DF.Check
        sql: DF.Code | None
        time_taken: DF.Float
    # end: auto-generated types

    @staticmethod
    def clear_old_logs(days=90):
        from frappe.query_builder import Interval
        from frappe.query_builder.functions import Now

        # Retention below UNUSED_TABLE_DAYS (data_warehouse.py) makes the weekly
        # data store cleanup skip pruning: the default stays well above it.
        table = frappe.qb.DocType("Insights Query Execution Log")
        frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))


def on_doctype_update():
    # Tables created before frappe 16 have no creation index, and clear_old_logs deletes by creation.
    frappe.db.add_index("Insights Query Execution Log", ["creation"], index_name="creation")
