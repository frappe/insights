# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

MAX_FOLDER_TITLE_LENGTH = 50


class InsightsFolder(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        is_expanded: DF.Check
        sort_order: DF.Int
        title: DF.Data
        type: DF.Literal["query", "chart", "dashboard"]
        workbook: DF.Link | None
    # end: auto-generated types

    def validate(self):
        if len(self.title or "") > MAX_FOLDER_TITLE_LENGTH:
            frappe.throw(_("Folder name cannot exceed {0} characters").format(MAX_FOLDER_TITLE_LENGTH))

        if self.type == "dashboard":
            self.workbook = None
        elif not self.workbook:
            frappe.throw("Workbook is required for query and chart folders")
