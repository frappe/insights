# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class InsightsWorkbookQuery(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        execution_time: DF.Float
        last_execution: DF.Datetime | None
        operations: DF.JSON
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        result_row_count: DF.Int
        sql: DF.Code | None
        status: DF.Literal[
            "Pending Execution", "Execution Successful", "Execution Failed"
        ]
        title: DF.Data
    # end: auto-generated types
