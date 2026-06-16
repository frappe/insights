# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# Maximum nesting depth of workbook folders (1 = top level).
# Kept as a guard only; the data model supports arbitrary depth.
MAX_FOLDER_DEPTH = 2


class InsightsWorkbookFolder(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        name: DF.Int | None
        parent_folder: DF.Link | None
        title: DF.Data
    # end: auto-generated types

    def validate(self):
        self.validate_depth()

    def validate_depth(self):
        if not self.parent_folder:
            return

        if self.parent_folder == self.name:
            frappe.throw(_("A folder cannot be its own parent"))

        # depth of this folder = depth of parent + 1
        grandparent = frappe.db.get_value("Insights Workbook Folder", self.parent_folder, "parent_folder")
        if grandparent:
            frappe.throw(_("Folders can only be nested up to {0} levels deep").format(MAX_FOLDER_DEPTH))
