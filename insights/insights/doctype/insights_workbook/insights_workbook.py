# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document


class InsightsWorkbook(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from insights.insights.doctype.insights_workbook_chart.insights_workbook_chart import (
            InsightsWorkbookChart,
        )
        from insights.insights.doctype.insights_workbook_query.insights_workbook_query import (
            InsightsWorkbookQuery,
        )

        charts: DF.Table[InsightsWorkbookChart]
        queries: DF.Table[InsightsWorkbookQuery]
        title: DF.Data | None
    # end: auto-generated types

    def on_update(self):
        self.delete_removed_queries()

    def delete_removed_queries(self):
        doc_before_save = self.get_doc_before_save()
        if doc_before_save:
            queries = [row.query for row in self.queries]
            queries_before_save = [row.query for row in doc_before_save.queries]
            queries_to_delete = [
                query for query in queries_before_save if query not in queries
            ]
            for query in queries_to_delete:
                frappe.delete_doc("Insights Query", query)
