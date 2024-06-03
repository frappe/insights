# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InsightsWorkbookChart(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        chart_type: DF.Data
        config: DF.JSON
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        query: DF.Data
    # end: auto-generated types

    pass
