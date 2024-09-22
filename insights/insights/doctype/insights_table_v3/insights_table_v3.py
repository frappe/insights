# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from hashlib import md5

import frappe
from frappe.model.document import Document, bulk_insert

from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    DataWarehouse,
)


class InsightsTablev3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from insights.insights.doctype.insights_table_column.insights_table_column import (
            InsightsTableColumn,
        )

        columns: DF.Table[InsightsTableColumn]
        data_source: DF.Link
        label: DF.Data
        last_synced_on: DF.Datetime | None
        table: DF.Data
    # end: auto-generated types

    def autoname(self):
        self.name = get_table_name(self.data_source, self.table)

    @staticmethod
    def bulk_create(data_source: str, tables: list[str]):
        table_docs = []
        for table in tables:
            doc = frappe.new_doc("Insights Table v3")
            doc.name = get_table_name(data_source, table)
            doc.data_source = data_source
            doc.table = table
            doc.label = table
            table_docs.append(doc)

        bulk_insert("Insights Table v3", table_docs)

    @staticmethod
    def get_ibis_table(data_source, table, use_live_connection=False):
        from insights.insights.doctype.insights_team.insights_team import (
            apply_table_restrictions,
            check_table_permission,
        )

        check_table_permission(data_source, table)
        t = DataWarehouse().get_table(
            data_source,
            table,
            use_live_connection=use_live_connection,
        )
        t = apply_table_restrictions(t, data_source, table)
        return t

    @frappe.whitelist()
    def import_to_data_warehouse(self):
        frappe.only_for("Insights Admin")
        DataWarehouse().import_remote_table(
            self.data_source,
            self.table,
            force=True,
        )


def get_table_name(data_source, table):
    return md5((data_source + table).encode()).hexdigest()[:10]
