# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class InsightsAlertQuery(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        alias: DF.Data
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        query: DF.Link
    # end: auto-generated types

    pass
