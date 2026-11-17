# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from insights import standard


class InsightsFolder(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        is_expanded: DF.Check
        sort_order: DF.Int
        title: DF.Data
        type: DF.Literal["query", "chart"]
        workbook: DF.Link
    # end: auto-generated types

    def validate(self):
        standard.guard_member(self)
        self.validate_title()

    def validate_title(self):
        """Keep folder titles unique per type within a workbook.

        A workbook file identifies a folder by its title. A new folder takes the
        next free title, as the New folder button and a restore both expect. A
        rename to a taken title is the author's choice, so it is refused.
        """
        taken = set(
            frappe.get_all(
                "Insights Folder",
                filters={"workbook": self.workbook, "type": self.type, "name": ["!=", self.name]},
                pluck="title",
            )
        )
        if self.title not in taken:
            return
        if not self.is_new():
            frappe.throw(
                frappe._("A {0} folder titled {1} already exists.").format(self.type, frappe.bold(self.title))
            )
        self.title = next_free_title(self.title, taken)

    def on_update(self):
        standard.export_member(self)

    def before_rename(self, old_name, new_name, merge=False):
        standard.guard_member(self)

    def after_rename(self, old_name, new_name, merge=False):
        standard.export_member(self)

    def on_trash(self):
        standard.guard_member(self)

    def after_delete(self):
        standard.export_member(self)


def next_free_title(title: str, taken: set[str]) -> str:
    """`title` numbered past every title in `taken`: "Untitled 2", then "Untitled 3"."""
    number = 2
    while f"{title} {number}" in taken:
        number += 1
    return f"{title} {number}"
