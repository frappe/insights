# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InsightsWorkbookSnapshot(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        snapshot: DF.JSON
        title: DF.Data | None
        workbook: DF.Link
    # end: auto-generated types

    def before_insert(self):
        if not self.has_changed():
            frappe.throw("No changes detected since the last snapshot.")

    def has_changed(self):
        last_snapshot = self.get_last_snapshot()
        if not last_snapshot:
            return True

        last_data = frappe.parse_json(last_snapshot.snapshot)
        current_data = frappe.parse_json(self.snapshot)

        return self._compare_data(last_data, current_data)

    def get_last_snapshot(self):
        """Get the last snapshot for the associated workbook"""
        last_snapshot = frappe.get_all(
            "Insights Workbook Snapshot",
            filters={"workbook": self.workbook},
            fields=["name", "snapshot"],
            order_by="creation desc",
            limit=1,
        )
        if last_snapshot:
            return frappe.get_doc("Insights Workbook Snapshot", last_snapshot[0].name)
        return None

    def _compare_data(self, last_data, current_data):
        if not isinstance(last_data, dict) or not isinstance(current_data, dict):
            return last_data != current_data

        curr_normalized = frappe._dict(current_data)
        last_normalized = frappe._dict(last_data)

        curr_normalized.pop("timestamp", None)
        curr_normalized.pop("version", None)
        last_normalized.pop("timestamp", None)
        last_normalized.pop("version", None)

        return curr_normalized != last_normalized
