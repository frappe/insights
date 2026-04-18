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
    CircularQueryReferenceError,
    IbisQueryBuilder,
    execute_ibis_query,
    get_columns_from_schema,
)
from insights.insights.query_utils import (
    extract_query_deps_from_operations,
    find_cycle,
    transitive_closure,
)
from insights.utils import deep_convert_dict_to_dict

try:
    from frappe.concurrency_limiter import concurrent_limit
except ImportError:
    # Fallback no-op decorator if concurrency_limiter is not available (e.g. in older versions of Frappe)
    def concurrent_limit(limit=None, wait_timeout=None):
        def decorator(func):
            return func

        return decorator


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

    def validate(self):
        self._validate_no_circular_dependency()

    def _validate_no_circular_dependency(self):
        """Raise an error if the current operations would create a circular query reference."""
        operations = frappe.parse_json(self.operations) or []
        new_direct_deps = extract_query_deps_from_operations(operations)

        if not new_direct_deps:
            return

        cycle = find_cycle(self.name, new_direct_deps)
        if cycle:
            path_str = " → ".join(
                f'"{frappe.db.get_value("Insights Query v3", q, "title") or q}"' for q in cycle
            )
            frappe.throw(
                f"Circular query reference detected: {path_str}",
                exc=CircularQueryReferenceError,
            )

    def before_save(self):
        self.set_linked_queries()

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
        operations = frappe.parse_json(self.operations) or []
        self.linked_queries = extract_query_deps_from_operations(operations)

    def get_source_tables(self):
        """Collect all leaf table references from this query and its dependencies."""
        all_query_names = {self.name} | transitive_closure(self.name)
        source_tables = []

        for query_name in all_query_names:
            if query_name == self.name:
                operations = frappe.parse_json(self.operations) or []
            else:
                operations = (
                    frappe.parse_json(frappe.db.get_value("Insights Query v3", query_name, "operations"))
                    or []
                )

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
    @concurrent_limit()
    def execute(
        self,
        active_operation_idx: int | None = None,
        adhoc_filters: dict | None = None,
        force: bool = False,
        page: int = 1,
        page_size: int = 100,
    ):
        with set_adhoc_filters(adhoc_filters):
            ibis_query = self.build(active_operation_idx)

        results, time_taken = execute_ibis_query(
            ibis_query,
            page=page,
            page_size=page_size,
            force=force,
            cache_expiry=60 * 10,
            reference_doctype=self.doctype,
            reference_name=self.name,
        )
        results = results.to_dict(orient="records")

        columns = get_columns_from_schema(ibis_query.schema())
        return {
            "sql": ibis.to_sql(ibis_query),
            "columns": columns,
            "rows": results,
            "time_taken": time_taken,
        }

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
        count_results, _time_taken = execute_ibis_query(
            count_query,
            cache_expiry=60 * 5,
            reference_doctype=self.doctype,
            reference_name=self.name,
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
            page_size=10_00_000,
            reference_doctype=self.doctype,
            reference_name=self.name,
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
        result, _time_taken = execute_ibis_query(
            values_query,
            cache_expiry=24 * 60 * 60,
            reference_doctype=self.doctype,
            reference_name=self.name,
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
