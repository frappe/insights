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

    if table_name == "tabSingles":
        single_doctypes = frappe.get_all(
            "DocType", filters={"issingle": 1}, pluck="name"
        )
        allowed_doctypes = get_valid_perms()
        allowed_doctypes = [p.parent for p in allowed_doctypes if p.read]
        allowed_single_doctypes = set(single_doctypes) & set(allowed_doctypes)
        if len(allowed_single_doctypes) == len(single_doctypes):
            return t
        return t.filter(t.doctype.isin(allowed_single_doctypes))

    doctype = table_name.replace("tab", "")
    allowed_docs = get_allowed_documents(doctype)

    if allowed_docs == "*":
        return t
    if isinstance(allowed_docs, list):
        return t.filter(t.name.isin(allowed_docs))

    create_toast("You do not have permissions to access this table", type="error")
    return t.filter(False)


def get_allowed_documents(doctype):
    docs = []

    istable = frappe.get_meta(doctype).istable

    if not istable and frappe.has_permission(doctype):
        docs = frappe.get_list(doctype, pluck="name")
        doc_count = frappe.db.count(doctype)
        if doc_count == len(docs):
            docs = "*"

    if istable:
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

        parent_docs_by_doctype = {
            parent_doctype: get_allowed_documents(parent_doctype)
            for parent_doctype in parent_doctypes
        }

        CHILD_DOCTYPE = frappe.qb.DocType(child_doctype)
        docs_query = frappe.qb.from_(CHILD_DOCTYPE).select(CHILD_DOCTYPE.name)
        condition = None
        for parent_doctype, parent_docs in parent_docs_by_doctype.items():
            if parent_docs == "*":
                _cond = CHILD_DOCTYPE.parenttype == parent_doctype
                condition = _cond if condition is None else condition | _cond
            elif parent_docs:
                _cond = (CHILD_DOCTYPE.parenttype == parent_doctype) & (
                    CHILD_DOCTYPE.parent.isin(parent_docs)
                )
                condition = _cond if condition is None else condition | _cond

        docs = docs_query.where(condition).run(pluck="name")
        doc_count = frappe.db.count(doctype)
        if doc_count == len(docs):
            docs = "*"

    return docs
