# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import os
from datetime import datetime
from hashlib import md5

import frappe
import ibis
import pandas as pd
from frappe.model.document import Document
from frappe.permissions import get_valid_perms
from frappe.query_builder.functions import IfNull
from frappe.utils.safe_exec import safe_exec

from insights import create_toast
from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
    Warehouse,
    get_warehouse_folder_path,
    get_warehouse_table_name,
)
from insights.utils import InsightsDataSourcev3


class InsightsTablev3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        data_script: DF.Code | None
        data_source: DF.Link
        label: DF.Data
        last_synced_on: DF.Datetime | None
        stored: DF.Check
        sync_context: DF.Code | None
        table: DF.Data
        warehouse_sync_enabled: DF.Check
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

        if frappe.db.get_value(
            "Insights Table v3",
            get_table_name(data_source, table_name),
            "warehouse_sync_enabled",
        ):
            warehouse = Warehouse()
            return warehouse.db.read_parquet(
                os.path.join(
                    get_warehouse_folder_path(),
                    data_source,
                    table_name,
                ),
                table_name=get_warehouse_table_name(data_source, table_name),
            )

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

        if not self.warehouse_sync_enabled:
            frappe.throw("Warehouse sync is not enabled for this table")

        if self.import_in_progress():
            create_toast(
                f"Import for {frappe.bold(self.table)} is in progress."
                "You may not see the results till the import is completed.",
                title="Import In Progress",
                type="info",
                duration=7,
            )
            return

        self.calculate_batch_size()
        self.create_import_log()

        n = 0

        while True:
            data = self.run_data_script()
            if len(data) == 0:
                break

            self.create_parquet_file(data)

            primary_key = self.get_sync_context("primary_key")
            last_value = data[primary_key].max()
            self.update_sync_context("last_value", last_value)

            n += 1

            create_toast(
                f"Importing {frappe.bold(self.table)} to the data store. "
                f"{n} files created so far.",
                title="Import In Progress",
                type="info",
            )

        self.log.db_set(
            {
                "ended_at": frappe.utils.now(),
                "status": "Completed",
            },
        )
        create_toast(
            f"Import for {frappe.bold(self.table)} completed successfully. {n} files created.",
            title="Import Completed",
            duration=7,
        )

    def import_in_progress(self):
        log = frappe.qb.DocType("Insights Table Import Log")
        return frappe.db.exists(
            log,
            (
                (log.data_source == self.data_source)
                & (log.table_name == self.table)
                & (log.status == "In Progress")
                & (IfNull(log.ended_at, "") == "")
            ),
        )

    def create_import_log(self):
        self.log = frappe.new_doc("Insights Table Import Log")
        self.log.db_insert()
        self.log.db_set(
            {
                "data_source": self.data_source,
                "table_name": self.table,
                "started_at": frappe.utils.now(),
                "status": "In Progress",
            },
        )

        create_toast(
            f"Importing {frappe.bold(self.table)} to the data store. "
            "You may not see the results till the import is completed.",
            title="Import Started",
            duration=7,
        )

    def calculate_batch_size(self):
        if self.get_sync_context("batch_size"):
            return

        memory_limit = 512
        sample_size = 10
        sample_data = self.run_data_script({"batch_size": sample_size})
        total_size = sum(
            sample_data[column].memory_usage(deep=True)
            for column in sample_data.columns
        )
        row_size = total_size / sample_size / (1024 * 1024)
        batch_size = int(memory_limit / row_size)
        self.update_sync_context("batch_size", batch_size)

    def run_data_script(self, context=None):
        if not self.data_script:
            frappe.throw("Data script is not defined for this table")

        data = []
        context = context or frappe.parse_json(self.sync_context)
        context = frappe._dict(context)
        try:
            _, _locals = safe_exec(
                self.data_script,
                _globals={
                    "context": context,
                    "pandas": frappe._dict({"DataFrame": pd.DataFrame}),
                },
                _locals={"data": data},
                restrict_commit_rollback=True,
            )
            data = _locals["data"]
        except Exception as e:
            frappe.log_error(f"Error in data script for {self.table}: {e}")
            raise e

        if data is None:
            frappe.throw(
                "Data script returned None. Please ensure it returns a DataFrame"
            )

        if not isinstance(data, pd.DataFrame):
            frappe.throw("Data script must return a pandas DataFrame")

        return data

    def create_parquet_file(self, data):
        warehouse_folder = get_warehouse_folder_path()
        parquet_folder = os.path.join(warehouse_folder, self.data_source, self.table)
        if not os.path.exists(parquet_folder):
            os.makedirs(parquet_folder)

        random_hash = frappe.generate_hash(length=5)
        date_plus_hash = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{random_hash}"
        file_name = f"{date_plus_hash}.parquet"

        path = os.path.join(parquet_folder, file_name)

        table = ibis.memtable(data)
        table.to_parquet(path, compression="snappy")

    def update_sync_context(self, key, value):
        context = frappe.parse_json(self.sync_context) or {}
        context[key] = value
        self.db_set("sync_context", frappe.as_json(context), commit=True)

    def get_sync_context(self, key):
        context = frappe.parse_json(self.sync_context) or {}
        return context.get(key)


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
