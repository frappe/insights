# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class InsightsUpgradeItem(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        action: DF.Literal["", "delete_workbook", "open_settings"]
        code: DF.Data
        data: DF.JSON | None
        message: DF.SmallText
        reference_doctype: DF.Link | None
        reference_name: DF.DynamicLink | None
        status: DF.Literal["Open", "Done", "Dismissed"]
        user: DF.Link | None
    # end: auto-generated types

    pass
