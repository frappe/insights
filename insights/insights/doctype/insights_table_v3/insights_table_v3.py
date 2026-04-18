# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from hashlib import md5

import frappe
import ibis
from frappe.model.document import Document
from frappe.permissions import get_valid_perms
from frappe.query_builder.functions import Count, Max, Sum
from ibis import Table
from ibis.backends.duckdb import Backend as DuckDBBackend

import insights
from insights.utils import InsightsDataSourcev3


class InsightsTablev3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        before_import_script: DF.Code | None
        data_source: DF.Link
        label: DF.Data
        last_synced_on: DF.Datetime | None
        row_limit: DF.Int
        stored: DF.Check
        table: DF.Data
    # end: auto-generated types

    def autoname(self):
        self.name = get_table_name(self.data_source, self.table)

    def validate(self):
        if self.before_import_script:
            from insights.insights.doctype.insights_data_source_v3.ibis_utils import exec_with_return

            try:
                table = self.get_ibis_table(self.data_source, self.table, use_live_connection=True)
                exec_with_return(self.before_import_script, {"table": table})
            except Exception as e:
                frappe.throw(f"Error executing before import script: {e}")

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

        # TODO: replace with frappe.has_permission()
        check_table_permission(data_source, table_name)

        ds_type = frappe.db.get_value("Insights Data Source v3", data_source, "type", cache=True)
        if not use_live_connection and ds_type != "REST API":
            wt = insights.warehouse.get_table(data_source, table_name)
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
        wt = insights.warehouse.get_table(self.data_source, self.table)
        wt.enqueue_import()

    @frappe.whitelist()
    def get_stats(self):
        """Return usage and sync statistics for this table."""
        return get_table_stats(self.data_source, self.table)


def get_table_name(data_source, table):
    return md5((data_source + table).encode()).hexdigest()[:10]


def get_table_stats(data_source: str, table_name: str) -> dict:
    """Derive usage and sync stats for a warehouse table from existing data.

    Returns:
        - last_synced_on: last successful import timestamp
        - last_import_rows: row count from the most recent import
        - last_import_duration: duration (seconds) of the most recent import
        - referencing_queries: list of query names/titles that currently reference this table
        - last_executed_on: when the most recent referencing query was last executed
        - execution_count: total executions across all referencing queries
        - total_syncs: total number of import attempts
        - total_sync_time: sum of all import durations (seconds)
        - failed_syncs: number of failed imports
    """
    ImportLog = frappe.qb.DocType("Insights Table Import Log")

    last_import = (
        frappe.qb.from_(ImportLog)
        .select(ImportLog.rows_imported, ImportLog.time_taken)
        .where(
            (ImportLog.data_source == data_source)
            & (ImportLog.table_name == table_name)
            & (ImportLog.status == "Success")
        )
        .orderby(ImportLog.creation, order=frappe.qb.desc)
        .limit(1)
        .run(as_dict=True)
    )

    import_agg = (
        frappe.qb.from_(ImportLog)
        .select(
            Count("*").as_("total_syncs"),
            Sum(ImportLog.time_taken).as_("total_sync_time"),
            Count(frappe.qb.terms.Case().when(ImportLog.status == "Failed", 1)).as_("failed_syncs"),
        )
        .where((ImportLog.data_source == data_source) & (ImportLog.table_name == table_name))
        .run(as_dict=True)
    )

    last_synced_on, last_import_rows, last_import_duration = None, 0, 0
    table_doc = frappe.db.get_value(
        "Insights Table v3",
        get_table_name(data_source, table_name),
        ["last_synced_on"],
        as_dict=True,
    )
    if table_doc:
        last_synced_on = table_doc.last_synced_on
    if last_import:
        last_import_rows = last_import[0].get("rows_imported") or 0
        last_import_duration = last_import[0].get("time_taken") or 0

    referencing_queries = _get_referencing_queries(data_source, table_name)
    query_names = [q["name"] for q in referencing_queries]

    last_executed_on = None
    execution_count = 0
    if query_names:
        ExecLog = frappe.qb.DocType("Insights Query Execution Log")
        exec_stats = (
            frappe.qb.from_(ExecLog)
            .select(
                Max(ExecLog.creation).as_("last_executed_on"),
                Count("*").as_("execution_count"),
            )
            .where(ExecLog.query.isin(query_names))
            .run(as_dict=True)
        )
        if exec_stats:
            last_executed_on = exec_stats[0].get("last_executed_on")
            execution_count = exec_stats[0].get("execution_count") or 0

    agg = import_agg[0] if import_agg else {}
    return {
        "last_synced_on": last_synced_on,
        "last_import_rows": last_import_rows,
        "last_import_duration": last_import_duration,
        "total_syncs": agg.get("total_syncs") or 0,
        "total_sync_time": agg.get("total_sync_time") or 0,
        "failed_syncs": agg.get("failed_syncs") or 0,
        "referencing_queries": referencing_queries,
        "last_executed_on": last_executed_on,
        "execution_count": execution_count,
    }


def _get_referencing_queries(data_source: str, table_name: str) -> list[dict]:
    """Find all Insights Query v3 docs whose operations JSON references this table."""
    try:
        from frappe.query_builder.functions import JSONContains
    except ImportError:
        return []

    candidate = {"table": {"data_source": data_source, "table_name": table_name}}
    Query = frappe.qb.DocType("Insights Query v3")
    return (
        frappe.qb.from_(Query)
        .select(Query.name, Query.title, Query.workbook)
        .where(JSONContains(Query.operations, candidate))
        .run(as_dict=True)
    )


def apply_user_permissions(t: Table, data_source, table_name):
    if not frappe.db.get_value("Insights Data Source v3", data_source, "is_site_db", cache=True):
        return t

    if not frappe.db.get_single_value("Insights Settings", "apply_user_permissions", cache=True):
        return t

    if table_name == "tabSingles":
        single_doctypes = frappe.get_all("DocType", filters={"issingle": 1}, pluck="name")
        allowed_doctypes = get_valid_perms()
        allowed_doctypes = [p.parent for p in allowed_doctypes if p.read]
        allowed_single_doctypes = set(single_doctypes) & set(allowed_doctypes)
        if not allowed_single_doctypes:
            return t.filter(False)
        if len(allowed_single_doctypes) == len(single_doctypes):
            return t
        return t.filter(t.doctype.isin(allowed_single_doctypes))

    permission_query = get_permission_query_for_table(table_name)
    if not permission_query:
        return t.filter(False)

    if not _has_where_clause(permission_query):
        return t

    from_warehouse = isinstance(t.get_backend(), DuckDBBackend)
    if not from_warehouse:
        return t.sql(permission_query)

    # if from warehouse,
    # we will have to transform the `permission_query` to duckdb dialect and also replace the table names from `tabX` to `site_db.tabX` to use it as a subquery to filter the table `t`
    # to avoid the complexity of transforming the `permission_query` to duckdb dialect, we will execute the `permission_query` separately and get the list of permitted names and then filter the table `t` using semi_join

    if "name" not in t.columns:
        frappe.throw(
            f"Cannot apply user permissions for table {table_name} because it does not have a `name` column"
        )

    db = InsightsDataSourcev3.get_doc(data_source)._get_ibis_backend()
    names_expr = ibis.memtable(db.sql(permission_query).select("name"))
    return t.semi_join(names_expr, "name")


def get_permission_query_for_table(table_name) -> str | None:
    doctype = table_name.removeprefix("tab")
    istable = frappe.get_meta(doctype).istable

    if not istable and frappe.has_permission(doctype, "read"):
        permitted_docs_query = get_permission_query(doctype)
        return permitted_docs_query

    if istable:
        # For child tables:
        # 1. Find all the parent doctypes of the child table
        # 2. Filter out the non-permitted parent doctypes
        # 3. Call `get_list` for each permitted parent doctype
        # 4. Union all the queries

        child_doctype = doctype
        parent_doctypes = get_parents(child_doctype)
        permitted_parent_doctypes = [p for p in parent_doctypes if frappe.has_permission(p, "read")]

        if not permitted_parent_doctypes:
            return None

        child_perm_queries = []
        for parent_doctype in permitted_parent_doctypes:
            permitted_child_docs_query = get_permission_query(child_doctype, parent_doctype)
            child_perm_queries.append(permitted_child_docs_query)

        final_query = " UNION ALL ".join(child_perm_queries)
        return final_query

    return None


def get_permission_query(doctype, parent_doctype=None):
    return str(
        frappe.get_list(
            doctype,
            fields="*",
            order_by=None,
            parent_doctype=parent_doctype,
            run=False,
        )
    )


def get_parents(child_doctype):
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

    custom_parent_doctypes = frappe.get_all(
        "Custom Field",
        filters={
            "fieldtype": ["in", ["Table", "Table MultiSelect"]],
            "options": child_doctype,
        },
        pluck="dt",
        distinct=True,
    )

    return list(set(parent_doctypes + custom_parent_doctypes))


def _has_where_clause(sql: str) -> bool:
    return " where " in sql.lower()
