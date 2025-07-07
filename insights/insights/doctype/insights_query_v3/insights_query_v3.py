# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from contextlib import contextmanager

import frappe
import ibis
from frappe.model.document import Document
from ibis import _

from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
    execute_ibis_query,
    get_columns_from_schema,
)
from insights.utils import deep_convert_dict_to_dict


class InsightsQueryv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from insights.insights.doctype.insights_query_variable.insights_query_variable import InsightsQueryVariable

        is_builder_query: DF.Check
        is_native_query: DF.Check
        is_script_query: DF.Check
        linked_queries: DF.JSON | None
        old_name: DF.Data | None
        operations: DF.JSON | None
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

    def before_save(self):
        self.set_linked_queries()

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
    def execute(self, active_operation_idx=None, adhoc_filters=None, force=False):
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
    def get_count(self, active_operation_idx=None):
        ibis_query = self.build(active_operation_idx)
        count_query = ibis_query.aggregate(count=_.count())
        count_results, time_taken = execute_ibis_query(
            count_query,
            cache_expiry=60 * 5,
            reference_doctype=self.doctype,
            reference_name=self.name,
        )
        total_count = count_results.values[0][0]
        return int(total_count)

    @insights_whitelist()
    def download_results(self, active_operation_idx=None):
        ibis_query = self.build(active_operation_idx)
        results, time_taken = execute_ibis_query(
            ibis_query,
            cache=False,
            limit=10_00_000,
            reference_doctype=self.doctype,
            reference_name=self.name,
        )
        return results.to_csv(index=False)

    @insights_whitelist()
    def get_distinct_column_values(self, column_name, active_operation_idx=None, search_term=None, limit=20):
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
        )
        return result[column_name].tolist()

    @insights_whitelist()
    def get_columns_for_selection(self, active_operation_idx=None):
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


def import_query(query, workbook):
    query = frappe.parse_json(query)
    query = deep_convert_dict_to_dict(query)

    new_query = frappe.new_doc("Insights Query v3")
    new_query.update(query.doc)
    new_query.workbook = workbook
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
    frappe.local.insights_adhoc_filters = filters or {}
    yield
    frappe.local.insights_adhoc_filters = None
