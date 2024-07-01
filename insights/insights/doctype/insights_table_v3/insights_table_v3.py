# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    get_warehouse_table_name,
)
from insights.insights.doctype.insights_table_column.insights_table_column import (
    InsightsTableColumn,
)
from insights.insights.doctype.insights_table_link.insights_table_link import (
    InsightsTableLink,
)


class InsightsTablev3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        columns: DF.Table[InsightsTableColumn]
        data_source: DF.Link
        is_query_based: DF.Check
        label: DF.Data
        last_synced_on: DF.Datetime | None
        table: DF.Data
        table_links: DF.Table[InsightsTableLink]
    # end: auto-generated types

    def autoname(self):
        self.name = get_warehouse_table_name(self.data_source, self.table)


def sync_insights_table(
    data_source: str,
    table_name: str,
    columns: list[InsightsTableColumn] | None = None,
    table_links: list[InsightsTableLink] | None = None,
    force: bool = False,
):
    exists = frappe.db.exists(
        "Insights Table v3",
        {
            "data_source": data_source,
            "table": table_name,
        },
    )
    if exists and not force:
        return

    doc_before = None
    if docname := exists:
        doc = frappe.get_doc("Insights Table v3", docname)
        # using doc.get_doc_before_save() doesn't work here
        doc_before = frappe.get_cached_doc("Insights Table v3", docname)
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Insights Table v3",
                "data_source": data_source,
                "table": table_name,
                "label": table_name,
                "is_query_based": 0,
            }
        )

    doc.label = table_name
    if force:
        doc.columns = []
        doc.table_links = []

    for table_link in table_links or []:
        if not doc.get("table_links", table_link):
            doc.append("table_links", table_link)

    column_added = False
    for column in columns or []:
        # do not overwrite existing columns, since type or label might have been changed
        if any(doc_column.column == column.column for doc_column in doc.columns):
            continue
        doc.append("columns", column)
        column_added = True

    column_removed = False
    column_names = [c.column for c in columns]
    for column in doc.columns:
        if column.column not in column_names:
            doc.columns.remove(column)
            column_removed = True

    version = frappe.new_doc("Version")
    # if there's some update to store only then save the doc
    doc_changed = (
        version.update_version_info(doc_before, doc) or column_added or column_removed
    )
    is_new = not exists
    if is_new or doc_changed or force:
        # need to ignore permissions when creating/updating a table in query store
        # a user may have access to create a query and store it, but not to create a table
        doc.last_synced_on = frappe.utils.now()
        doc.save(ignore_permissions=True)
    return doc.name
