# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import base64
from contextlib import contextmanager, suppress
from io import BytesIO

import frappe
import ibis
import sqlglot
import sqlglot.expressions as sqlglot_exp
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
    get_direct_dependencies,
    referenced_queries,
    sync_query_references,
    table_references,
    transitive_closure,
)
from insights.utils import as_text, deep_convert_dict_to_dict


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
        return super().get_valid_dict(*args, **kwargs)

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)
        d.read_only = not self.has_permission("write")
        return d

    def on_trash(self):
        for alert in frappe.get_all("Insights Alert", filters={"query": self.name}, pluck="name"):
            frappe.delete_doc("Insights Alert", alert, force=True, ignore_permissions=True)

        # Remove all edges referencing or referenced by this query
        frappe.db.delete("Insights Query Reference", {"query": self.name})
        frappe.db.delete("Insights Query Reference", {"ref_query": self.name})

        # Clean up empty folders
        if self.folder:
            self.cleanup_empty_folder(self.folder)

    def validate(self):
        self._validate_no_circular_dependency()
        self._validate_referenced_queries()

    def _validate_referenced_queries(self):
        """A query may only reference a query its author can read.

        Only a newly added reference is checked, so an existing one stays saveable
        by anyone who may already read this query.
        """
        from insights.permissions import check_referenced_query_access

        before = self.get_doc_before_save()
        existing = referenced_queries(before.operations) if before else set()
        for dep in referenced_queries(self.operations) - existing:
            check_referenced_query_access(dep)

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

    def on_update(self):
        frappe.enqueue(
            sync_query_references,
            query_name=self.name,
            operations=self.operations,
            enqueue_after_commit=True,
            now=bool(frappe.flags.in_test),
        )

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

    def get_source_tables(self):
        """Collect all leaf table references from this query and its transitive dependencies.

        Which tables a query reads is a forward question, so each row answers its
        own. The edge table lags every write, and this runs right after a save.
        """
        seen: set[tuple] = set()
        tables = []
        for name in {self.name} | transitive_closure(self.name):
            operations = frappe.db.get_value("Insights Query v3", name, "operations")
            for ref in table_references(operations):
                key = (ref["data_source"], ref["table_name"])
                if key in seen:
                    continue
                seen.add(key)
                tables.append(ref)
        return tables

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

        sql = None
        with suppress(Exception):
            for op in frappe.parse_json(self.operations) or []:
                if op.get("type") == "sql" and op.get("raw_sql"):
                    sql = op.get("raw_sql")
                    break

        return {
            "sql": ibis.to_sql(ibis_query),
            "columns": columns,
            "rows": results,
            "time_taken": time_taken,
            "is_aggregated_sql": _sql_has_group_by(sql) if sql else False,
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
        from insights.insights.doctype.insights_team.insights_team import is_admin

        if not is_admin(frappe.session.user) and not frappe.db.get_single_value(
            "Insights Settings", "allow_download"
        ):
            frappe.throw(
                "You are not allowed to download data. Contact your administrator.",
                frappe.PermissionError,
            )

        if not is_admin(frappe.session.user) and not (
            frappe.has_permission(self.doctype, ptype="export")
            and frappe.has_permission(self.doctype, ptype="read", doc=self)
        ):
            frappe.throw(
                frappe._(
                    "Your role does not have the export permission for queries. Contact your administrator."
                ),
                frappe.PermissionError,
            )

        with set_adhoc_filters(adhoc_filters):
            ibis_query = self.build(active_operation_idx)

        import ibis.expr.datatypes as dt

        decimal_casts = {
            col: ibis_query[col].cast("float64")
            for col in ibis_query.columns
            if isinstance(ibis_query[col].type(), dt.Decimal)
        }
        if decimal_casts:
            ibis_query = ibis_query.mutate(**decimal_casts)

        if hasattr(ibis_query, "limit"):
            ibis_query = ibis_query.limit(100_000)

        results, _ = execute_ibis_query(
            ibis_query,
            cache=False,
            paginate=False,
            reference_doctype=self.doctype,
            reference_name=self.name,
        )

        results = as_text(results)
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
        from insights.permissions import check_referenced_query_access

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

        linked_queries = get_direct_dependencies(self.name)
        for q in linked_queries:
            # `on_trash` drops the edge rows but not the operations that name the
            # query, so a deleted reference is a name that resolves to nothing.
            if not frappe.db.exists("Insights Query v3", q):
                continue

            # export() recurses, so this covers the whole dependency tree
            check_referenced_query_access(q)
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


def _sql_has_group_by(sql: str) -> bool:
    """Return True if SQL contains a GROUP BY
    anywhere in its AST (including CTEs and subqueries that feed the outer SELECT).

    Uses sqlglot to parse the SQL so that GROUP BY inside string literals or
    comments is correctly ignored. Falls back to False on any parse error.

    The only residual false positive is a GROUP BY that appears exclusively
    inside a WHERE … IN (subquery) used for deduplication — negligible in
    practice for analytics SQL (DISTINCT is used instead).
    """
    try:
        statements = sqlglot.parse(sql)
        if statements:
            stmt = statements[-1]
            if stmt is not None and stmt.find(sqlglot_exp.Group) is not None:
                return True
    except Exception:
        pass
    return False


def already_in_workbook(query_name, workbook) -> bool:
    """Whether `query_name` is a query the target workbook already holds.

    A reference that resolves here needs no copy, and the copy would be a second
    row for one query. The file cannot answer this: it carries the exporting
    site's workbook name, and `autoname` makes those a bare counter, so every
    site has a workbook "1". Ask the row.
    """
    if not query_name:
        return False

    return frappe.db.get_value("Insights Query v3", query_name, "workbook") == workbook


def import_query(query, workbook, id_map=None):
    """Copy an exported query into `workbook`, references and all.

    The dependencies go in first, so the query is inserted already naming the
    copies that replace them. It is never stored naming the exporting site's
    queries, which is a state `validate` would read as the real one.

    `export` nests, so a query two branches both build on appears once per branch.
    `id_map` is shared down the recursion, so it is imported once.
    """
    from insights.insights.doctype.insights_workbook.insights_workbook import (
        _rewrite_query_references,
    )

    query = frappe.parse_json(query)
    query = deep_convert_dict_to_dict(query)

    id_map = {} if id_map is None else id_map
    for name, dependency in ((query.get("dependencies") or {}).get("queries") or {}).items():
        if name in id_map or already_in_workbook(name, workbook):
            continue
        id_map[name] = import_query(dependency, workbook, id_map)

    new_query = frappe.new_doc("Insights Query v3")
    new_query.update(query.doc)
    new_query.workbook = workbook
    new_query.operations = _rewrite_query_references(query.doc.operations, id_map)

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

    return new_query.name


@contextmanager
def set_adhoc_filters(filters):
    # If frappe.local.insights_adhoc_filters exists but is None, getattr returns None.
    # We must ensure it's a dict.
    current = getattr(frappe.local, "insights_adhoc_filters", None)
    frappe.local.insights_adhoc_filters = filters or current or {}
    yield
    frappe.local.insights_adhoc_filters = None
