# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InsightsResourcePermission(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        name: DF.Int | None
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        resource_name: DF.DynamicLink
        resource_type: DF.Link
        table_restrictions: DF.Data | None
    # end: auto-generated types

    pass
