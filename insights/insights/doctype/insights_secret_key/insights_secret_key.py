# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InsightsSecretKey(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        key: DF.Data
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        value: DF.Password
    # end: auto-generated types

    pass
