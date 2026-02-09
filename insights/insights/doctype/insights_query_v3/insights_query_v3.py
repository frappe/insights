# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import base64
from contextlib import contextmanager
from io import BytesIO

import frappe
import ibis
import sqlparse
from frappe.model.document import Document
from ibis import _

from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
    execute_ibis_query,
    get_columns_from_schema,
    is_query_executing,
    release_lock,
    release_semaphore,
    try_acquire_lock,
    try_acquire_semaphore,
)
from insights.utils import deep_convert_dict_to_dict


class InsightsQueryv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from insights.insights.doctype.insights_query_variable.insights_query_variable import (
            InsightsQueryVariable,
        )

        folder: DF.Data | None
        is_builder_query: DF.Check
        is_native_query: DF.Check
        is_script_query: DF.Check
        linked_queries: DF.JSON | None
        old_name: DF.Data | None
        operations: DF.JSON | None
        sort_order: DF.Int
        title: DF.Data | None
        use_live_connection: DF.Check
        variables: DF.Table[InsightsQueryVariable]
        workbook: DF.Link
    # end: auto-generated types

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.operations, list):
            self.operations = frappe.as_json(self.operations)
        if isinstance(self.linked_queries, list):
            self.linked_queries = frappe.as_json(self.linked_queries)
        return super().get_valid_dict(*args, **kwargs)

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)
        d.read_only = not self.has_permission("write")
        return d

    def on_trash(self):
        for alert in frappe.get_all("Insights Alert", filters={"query": self.name}, pluck="name"):
            frappe.delete_doc("Insights Alert", alert, force=True, ignore_permissions=True)

        # Clean up empty folders
        if self.folder:
            self.cleanup_empty_folder(self.folder)

    def before_save(self):
        self.set_linked_queries()

    def _get_execution_lock_key(self):
        return f"insights_query_exec:{self.name}"

    def cleanup_empty_folder(self, folder_name):
        """Delete folder if it has no queries or charts"""
        if not frappe.db.exists("Insights Folder", folder_name):
            return

        folder = frappe.get_doc("Insights Folder", folder_name)
        folder_type = folder.type

        # Check if any queries/charts still use this folder
        if folder_type == "query":
            has_items = frappe.db.exists("Insights Query v3", {"folder": folder_name})
        else:
            has_items = frappe.db.exists("Insights Chart v3", {"folder": folder_name})

        if not has_items:
            frappe.delete_doc("Insights Folder", folder_name, force=True, ignore_permissions=True)

    def set_linked_queries(self):
        operations = frappe.parse_json(self.operations)
        if not operations:
            return

        linked_queries = []
        for operation in operations:
            if (
                operation.get("table")
                and operation.get("table").get("type") == "query"
                and operation.get("table").get("query_name")
            ):
                linked_queries.append(operation.get("table").get("query_name"))
        self.linked_queries = linked_queries

    def get_source_tables(self, visited=None):
        """Recursively collect all leaf table references from this query and its dependencies."""
        if visited is None:
            visited = set()

        # Prevent infinite recursion from circular dependencies
        if self.name in visited:
            return []
        visited.add(self.name)

        source_tables = []
        operations = frappe.parse_json(self.operations)

        if not operations:
            return source_tables

        # Collect direct table references from this query's operations
        for operation in operations:
            if operation.get("type") in ["source", "join", "union"]:
                table = operation.get("table")
                if table and table.get("type") == "table":
                    table_info = {
                        "data_source": table.get("data_source"),
                        "table_name": table.get("table_name"),
                    }
                    if table_info not in source_tables:
                        source_tables.append(table_info)

        # Recursively collect tables from linked queries
        linked_queries = frappe.parse_json(self.linked_queries)
        if linked_queries:
            for query_name in linked_queries:
                if query_name not in visited:
                    try:
                        linked_query = frappe.get_doc("Insights Query v3", query_name)
                        linked_tables = linked_query.get_source_tables(visited)
                        for table_info in linked_tables:
                            if table_info not in source_tables:
                                source_tables.append(table_info)
                    except Exception:
                        # Skip if linked query doesn't exist or can't be loaded
                        continue

        return source_tables

    def build(self, active_operation_idx=None, use_live_connection=None):
        builder = IbisQueryBuilder(self, active_operation_idx)
        builder.use_live_connection = (
            use_live_connection if use_live_connection is not None else self.use_live_connection
        )
        ibis_query = builder.build()

        if ibis_query is None:
            frappe.throw("Failed to build query")

        return ibis_query

    @frappe.whitelist()
    def execute(self, active_operation_idx=None, adhoc_filters=None, force=False, dashboard=None):
        lock_key = self._get_execution_lock_key()

        # before creating a db connection, check if query is executing
        if not force and is_query_executing(lock_key):
            return {
                "status": "pending",
                "cache_key": lock_key,
            }

        if not try_acquire_lock(lock_key):
            return {
                "status": "pending",
                "cache_key": lock_key,
            }

        try:
            slot = try_acquire_semaphore()
            if slot is None:
                return {"status": "queue_full"}

            try:
                with set_adhoc_filters(adhoc_filters):
                    ibis_query = self.build(active_operation_idx)

                limit = 100
                for op in frappe.parse_json(self.operations):
                    if op.get("limit"):
                        limit = op.get("limit")
                        break

                results, time_taken = execute_ibis_query(
                    ibis_query,
                    limit,
                    force=force,
                    cache_expiry=60 * 10,
                    reference_doctype=self.doctype,
                    reference_name=self.name,
                    use_lock=False,
                )

                if hasattr(results, "to_dict"):
                    rows = results.to_dict(orient="records")
                else:
                    rows = results

                columns = get_columns_from_schema(ibis_query.schema())
                sql = ibis.to_sql(ibis_query)

                self._cache_execution_result(
                    lock_key,
                    {
                        "sql": sql,
                        "columns": columns,
                        "rows": rows,
                        "time_taken": time_taken,
                    },
                )
                self._publish_query_complete(lock_key, dashboard)

                return {
                    "sql": sql,
                    "columns": columns,
                    "rows": rows,
                    "time_taken": time_taken,
                }

            finally:
                release_semaphore()
        finally:
            release_lock(lock_key)

    def _publish_query_complete(self, lock_key, dashboard=None):
        if not dashboard:
            return
        frappe.publish_realtime(
            "insights_query_complete",
            {"cache_key": lock_key},
            doctype="Insights Dashboard v3",
            docname=dashboard,
        )

    def _cache_execution_result(self, lock_key, result, cache_expiry=600):
        cache_key = f"insights:exec_result:{lock_key}"
        frappe.cache().set_value(cache_key, frappe.as_json(result), expires_in_sec=cache_expiry)

    def _get_cached_execution_result(self, lock_key):
        cache_key = f"insights:exec_result:{lock_key}"
        data = frappe.cache().get_value(cache_key)
        if data:
            return frappe.parse_json(data)
        return None

    # Check if a pending query has executed and return results
    # Used for polling when another process is executing the same query
    @insights_whitelist()
    def check_pending_result(self, cache_key):
        # Check if query is still executing
        if is_query_executing(cache_key):
            return {"status": "pending"}

        cached_result = self._get_cached_execution_result(cache_key)
        if cached_result:
            return {
                "status": "completed",
                "sql": cached_result.get("sql"),
                "columns": cached_result.get("columns"),
                "rows": cached_result.get("rows"),
                "time_taken": cached_result.get("time_taken"),
            }

        return {"status": "not_found"}

    @insights_whitelist()
    def format(self, raw_sql: str):
        if not raw_sql or not self.is_native_query:
            return raw_sql

        return sqlparse.format(str(raw_sql), reindent=True, keyword_case="upper")

    @insights_whitelist()
    def get_count(self, active_operation_idx: int | None = None, adhoc_filters: dict | None = None):
        with set_adhoc_filters(adhoc_filters):
            ibis_query = self.build(active_operation_idx)

        count_query = ibis_query.aggregate(count=_.count())
        count_results, time_taken = execute_ibis_query(
            count_query,
            cache_expiry=60 * 5,
            reference_doctype=self.doctype,
            reference_name=self.name,
            use_lock=False,
        )
        total_count = count_results.values[0][0]
        return int(total_count)

    @insights_whitelist()
    def download_results(
        self, format: str = "csv", active_operation_idx: int | None = None, adhoc_filters: dict | None = None
    ):
        with set_adhoc_filters(adhoc_filters):
            ibis_query = self.build(active_operation_idx)

        results, _ = execute_ibis_query(
            ibis_query,
            cache=False,
            limit=10_00_000,
            reference_doctype=self.doctype,
            reference_name=self.name,
            use_lock=False,
        )
        if format == "excel":
            output = BytesIO()
            results.to_excel(output, index=False, engine="openpyxl")
            excel_data = output.getvalue()
            return base64.b64encode(excel_data).decode("utf-8")
        else:
            return results.to_csv(index=False)

    @insights_whitelist()
    def get_distinct_column_values(
        self,
        column_name: str,
        active_operation_idx: int | None = None,
        search_term: str | None = None,
        limit: int = 20,
        adhoc_filters: dict | None = None,
    ):
        with set_adhoc_filters(adhoc_filters):
            ibis_query = self.build(active_operation_idx)

        values_query = (
            ibis_query.select(column_name)
            .filter(
                getattr(_, column_name).notnull()
                if not search_term
                else getattr(_, column_name).ilike(f"%{search_term}%")
            )
            .distinct()
            .head(limit)
        )
        result, time_taken = execute_ibis_query(
            values_query,
            cache_expiry=24 * 60 * 60,
            reference_doctype=self.doctype,
            reference_name=self.name,
            use_lock=False,
        )
        return result[column_name].tolist()

    @insights_whitelist()
    def get_columns_for_selection(self, active_operation_idx: int | None = None):
        ibis_query = self.build(active_operation_idx)
        columns = get_columns_from_schema(ibis_query.schema())
        return columns

    def evaluate_alert_expression(self, expression):
        builder = IbisQueryBuilder(self)
        ibis_query = builder.build()
        filter_expression = builder.evaluate_expression(expression)
        ibis_query = ibis_query.filter(filter_expression)
        ibis_query = ibis_query.limit(1)
        results, _ = execute_ibis_query(
            ibis_query,
            cache=False,
            reference_doctype=self.doctype,
            reference_name=self.name,
            use_lock=False,
        )
        return bool(len(results))

    @insights_whitelist()
    def export(self):
        query = {
            "version": "1.0",
            "timestamp": frappe.utils.now(),
            "type": "Query",
            "name": self.name,
            "doc": {
                "name": self.name,
                "title": self.title,
                "workbook": self.workbook,
                "use_live_connection": self.use_live_connection,
                "is_script_query": self.is_script_query,
                "is_builder_query": self.is_builder_query,
                "is_native_query": self.is_native_query,
                "operations": frappe.parse_json(self.operations),
            },
            "dependencies": {
                "queries": {},
            },
        }

        linked_queries = frappe.parse_json(self.linked_queries)
        for q in linked_queries:
            exported_query = frappe.get_doc("Insights Query v3", q).export()
            query["dependencies"]["queries"][q] = exported_query

        return query

    @insights_whitelist()
    def duplicate(self):
        new_query = frappe.copy_doc(self)
        new_query.title = f"{self.title} (Copy)"
        new_query.insert()
        return new_query.name

    @insights_whitelist(role="Insights Admin")
    def refresh_stored_tables(self):
        """Import all source tables used in this query to the data store"""
        source_tables = self.get_source_tables()
        if not source_tables:
            frappe.throw("No tables found in the query to import")

        imported_count = 0
        for table in source_tables:
            data_source = table.get("data_source")
            table_name = table.get("table_name")
            if data_source and table_name:
                from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

                table_doc_name = get_table_name(data_source, table_name)
                if frappe.db.exists("Insights Table v3", table_doc_name):
                    table_doc = frappe.get_doc("Insights Table v3", table_doc_name)
                    table_doc.import_to_warehouse()
                    imported_count += 1

        return {"message": f"Importing {imported_count} table(s) to data store", "count": imported_count}


def import_query(query, workbook):
    query = frappe.parse_json(query)
    query = deep_convert_dict_to_dict(query)

    new_query = frappe.new_doc("Insights Query v3")
    new_query.update(query.doc)
    new_query.workbook = workbook

    if not hasattr(new_query, "sort_order") or new_query.sort_order is None:
        max_sort_order = (
            frappe.db.get_value(
                "Insights Query v3",
                filters={"workbook": workbook},
                fieldname="max(sort_order)",
            )
            or -1
        )
        new_query.sort_order = max_sort_order + 1
    new_query.insert()

    if str(workbook) == str(query.doc.workbook) or not query.dependencies.queries:
        return new_query.name

    # if query is copied to a new workbook, all the dependencies will be copied as well
    # so we create a new query in the workbook for each dependency
    # and replace the old query names with the new query names

    id_map = {}
    for q, exported_query in query.dependencies.queries.items():
        id_map[q] = import_query(exported_query, workbook=new_query.workbook)

    # replace the old query names with the new query names
    operations = frappe.parse_json(new_query.operations)
    operations = deep_convert_dict_to_dict(operations)

    should_update = False
    for op in operations:
        if not op.get("table") or not op.get("table").get("type") or not op.get("table").get("query_name"):
            continue

        ref_query = op.table.query_name
        if ref_query in id_map:
            op.table.query_name = id_map[ref_query]
            should_update = True

    if should_update:
        new_query.db_set(
            "operations",
            frappe.as_json(operations),
            update_modified=False,
        )

    return new_query.name


@contextmanager
def set_adhoc_filters(filters):
    frappe.local.insights_adhoc_filters = filters or getattr(frappe.local, "insights_adhoc_filters", {})
    yield
    frappe.local.insights_adhoc_filters = None
