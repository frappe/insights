# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from hashlib import md5

import frappe
from frappe.model.document import Document
from frappe.permissions import get_valid_perms

from insights import create_toast
from insights.insights.doctype.insights_data_source_v3.data_warehouse import Warehouse
from insights.utils import InsightsDataSourcev3


class InsightsTablev3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        data_source: DF.Link
        label: DF.Data
        last_synced_on: DF.Datetime | None
        stored: DF.Check
        table: DF.Data
    # end: auto-generated types

    def autoname(self):
        self.name = get_table_name(self.data_source, self.table)

    @staticmethod
    def bulk_create(data_source: str, tables: list[str]):
        frappe.db.bulk_insert(
            "Insights Table v3",
            [
                "name",
                "data_source",
                "table",
                "label",
                "creation",
                "modified",
                "modified_by",
                "owner",
            ],
            [
                [
                    get_table_name(data_source, table),
                    data_source,
                    table,
                    table,
                    frappe.utils.now(),
                    frappe.utils.now(),
                    frappe.session.user,
                    frappe.session.user,
                ]
                for table in tables
            ],
            ignore_duplicates=True,
        )

    @staticmethod
    def get_ibis_table(data_source, table_name, use_live_connection=False):
        from insights.insights.doctype.insights_team.insights_team import (
            apply_table_restrictions,
            check_table_permission,
        )

        check_table_permission(data_source, table_name)

        if not use_live_connection:
            wt = Warehouse().get_table(data_source, table_name)
            t = wt.get_ibis_table(import_if_not_exists=True)
        else:
            ds = InsightsDataSourcev3.get_doc(data_source)
            t = ds.get_ibis_table(table_name)

        t = apply_table_restrictions(t, data_source, table_name)
        t = apply_user_permissions(t, data_source, table_name)
        return t

    @frappe.whitelist()
    def import_to_warehouse(self):
        frappe.only_for("Insights Admin")
        wt = Warehouse().get_table(self.data_source, self.table)
        wt.enqueue_import()


def get_table_name(data_source, table):
    return md5((data_source + table).encode()).hexdigest()[:10]


def apply_user_permissions(t, data_source, table_name):
    if not frappe.db.get_single_value(
        "Insights Settings", "apply_user_permissions", cache=True
    ):
        return t

    if not frappe.db.get_value(
        "Insights Data Source v3", data_source, "is_site_db", cache=True
    ):
        return t

    empty_table = t.filter(t.name.isnull())

    doctype = table_name.replace("tab", "")

    if not frappe.get_meta(doctype).istable:
        if not frappe.has_permission(doctype):
            create_toast(
                "You do not have permission to access this table", type="error"
            )
            return empty_table

        names = get_allowed_documents(doctype)

        if not names:
            return empty_table

        if names == "*":
            return t

        return t.filter(t.name.isin(names))

    # For child tables:
    # 1. Find all the parent doctypes of the child table
    # 2. Filter the parent doctypes where user has read permission
    # 3. Find all the allowed documents of the parent doctypes
    # 4. Filter child table where `parent` is in allowed documents

    child_doctype = doctype
    parent_doctypes = frappe.get_all(
        "DocField",
        filters={
            "parenttype": "DocType",
            "fieldtype": ["in", ["Table", "Table MultiSelect"]],
            "options": child_doctype,
        },
        pluck="parent",
        distinct=True,
    )

    doctype_perms = get_valid_perms()
    parent_doctypes = [
        p.parent for p in doctype_perms if p.read and p.parent in parent_doctypes
    ]

    if not parent_doctypes:
        create_toast("You do not have permission to access this table", type="error")
        return empty_table

    docs_by_doctype = {
        parent_doctype: get_allowed_documents(parent_doctype)
        for parent_doctype in parent_doctypes
    }

    condition = False
    for parent_doctype, docs in docs_by_doctype.items():
        if docs == "*":
            condition = condition | (t.parenttype == parent_doctype)
        elif docs:
            condition = condition | (
                (t.parenttype == parent_doctype) & (t.parent.isin(docs))
            )
        else:
            condition = condition | (
                (t.parenttype == parent_doctype) & (t.name.isnull())
            )

    return t.filter(condition)


def get_allowed_documents(doctype):
    names = frappe.get_list(doctype, pluck="name")
    doc_count = frappe.db.count(doctype)

    if doc_count == len(names):
        return "*"

    return names
