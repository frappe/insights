import ast
import re
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import date
from functools import cached_property

import frappe
import ibis
import numpy as np
import pandas as pd
import sqlglot as sg
import sqlparse
from frappe.utils.data import flt
from frappe.utils.safe_exec import SERVER_SCRIPT_FILE_PREFIX, safe_eval, safe_exec
from ibis import _
from ibis.expr.datatypes import DataType
from ibis.expr.operations.relations import DatabaseTable, Field
from ibis.expr.types import Expr
from ibis.expr.types import Table as IbisQuery

import insights
from insights import create_toast
from insights.cache_utils import make_digest
from insights.insights.doctype.insights_data_source_v3.data_warehouse import is_warehouse
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    InsightsTablev3,
)
from insights.insights.query_builders.sql_functions import (
    add_start_and_end_time,
    handle_timespan,
    resolve_timespan,
)
from insights.insights.query_utils import extract_sql_table_refs, get_direct_dependencies
from insights.utils import create_execution_log
from insights.utils import deep_convert_dict_to_dict as _dict

from .ibis.functions import fiscal_year_start, week_start
from .ibis.utils import assert_expression_has_no_io, get_functions

try:
    from frappe.concurrency_limiter import concurrent_limit
except ImportError:
    # Fallback no-op decorator if concurrency_limiter is not available (e.g. in older versions of Frappe)
    def concurrent_limit(limit=None, wait_timeout=None):
        def decorator(func):
            return func

        return decorator


# the relation a `sql_column` fragment selects from, standing for the pipeline so far
SQL_COLUMN_RELATION = "_insights_sql_column"


class CircularQueryReferenceError(frappe.ValidationError):
    """Raised when a circular query reference is detected during query building."""

    pass


class IbisQueryBuilder:
    def __init__(self, doc, active_operation_idx=None):
        self.doc = doc
        self.title = self.doc.title or self.doc.name
        self.active_operation_idx = active_operation_idx
        self.use_live_connection = bool(doc.use_live_connection)
        self.force = False
        self.operations = doc.operations
        self.set_operations()

    def set_operations(self):
        operations = frappe.parse_json(self.operations)
        adhoc_filters_by_query = getattr(frappe.local, "insights_adhoc_filters", None) or {}

        if (
            self.active_operation_idx is not None
            and self.active_operation_idx >= 0
            and self.active_operation_idx < len(operations)
        ):
            operations = operations[: self.active_operation_idx + 1]

        if self.doc.name in adhoc_filters_by_query:
            adhoc_filters = adhoc_filters_by_query[self.doc.name]
            if (
                adhoc_filters
                and isinstance(adhoc_filters, dict)
                and adhoc_filters.get("type") == "filter_group"
                and adhoc_filters.get("filters")
            ):
                # Filter out expression-based filters, keep only rule-based filters
                adhoc_filters["filters"] = [
                    f for f in adhoc_filters["filters"] if not f.get("expression", {}).get("type")
                ]
                if adhoc_filters["filters"]:
                    operations.append(adhoc_filters)

        self.operations = operations

    def build(self) -> IbisQuery:
        if not hasattr(frappe.local, "_insights_building_queries"):
            frappe.local._insights_building_queries = set()

        if self.doc.name in frappe.local._insights_building_queries:
            raise CircularQueryReferenceError(
                frappe._('Circular query reference detected while building "{0}"').format(self.title)
            )

        frappe.local._insights_building_queries.add(self.doc.name)
        try:
            self.query = None
            for idx, operation in enumerate(self.operations):
                try:
                    operation = _dict(operation)
                    self.query = self.perform_operation(operation)
                except CircularQueryReferenceError:
                    raise
                except BaseException as e:
                    operation_type_title = operation.type.title()
                    create_toast(
                        title=f"Failed to Build {self.title} Query",
                        message=f"Please check the {operation_type_title} operation at position {idx + 1}",
                        type="error",
                    )
                    raise e
            return self.query
        finally:
            frappe.local._insights_building_queries.discard(self.doc.name)

    def perform_operation(self, operation):
        if operation.type == "source":
            return self.apply_source(operation)
        elif operation.type == "join":
            return self.apply_join(operation)
        elif operation.type == "union":
            return self.apply_union(operation)
        elif operation.type == "filter":
            return self.apply_filter(operation)
        elif operation.type == "filter_group":
            return self.apply_filter_group(operation)
        elif operation.type == "select":
            return self.apply_select(operation)
        elif operation.type == "rename":
            return self.apply_rename(operation)
        elif operation.type == "remove":
            return self.apply_remove(operation)
        elif operation.type == "mutate":
            return self.apply_mutate(operation)
        elif operation.type == "sql_column":
            return self.apply_sql_column(operation)
        elif operation.type == "cast":
            return self.apply_cast(operation)
        elif operation.type == "summarize":
            return self.apply_summary(operation)
        elif operation.type == "order_by":
            return self.apply_order_by(operation)
        elif operation.type == "limit":
            return self.apply_limit(operation)
        elif operation.type == "pivot_wider":
            return self.apply_pivot(operation, "wider")
        elif operation.type == "custom_operation":
            return self.apply_custom_operation(operation)
        elif operation.type == "sql":
            return self.apply_sql(operation)
        elif operation.type == "code":
            return self.apply_code(operation)

        # Not `return self.query`: skipping an operation nobody recognises answers
        # with a table that is missing a column, a filter or a join, and nothing
        # says so. A query written by a newer client has to fail, not quietly
        # return different numbers.
        frappe.throw(
            frappe._("This query uses an operation this version does not know: {0}").format(operation.type),
        )

    @cached_property
    def saved_references(self):
        """The references this execution already carries authorisation for.

        Read from the row, not from the document being built: that one may have
        come from a request body, which authorises nothing.

        Two rows answer, because two kinds of document reach here under a name. A
        saved query carries the dependencies `validate` authorised. A chart runs a
        query document it mints from its config under the chart's own name, and
        what that pipeline sources is the chart's stored `query` link, which
        `check_chart_query_access` authorised when it was written.
        """
        name = self.doc.get("name")
        references = set(get_direct_dependencies(name))

        chart_query = frappe.db.get_value("Insights Chart v3", name, "query")
        if chart_query:
            references.add(chart_query)

        return references

    def check_query_reference(self, query_name):
        """A saved reference is authorised. Anything else is checked now."""
        if query_name in self.saved_references:
            return

        from insights.permissions import check_referenced_query_access

        check_referenced_query_access(query_name)

    def get_table_or_query(self, table_args):
        _table = None

        if table_args.type == "table":
            _table = InsightsTablev3.get_ibis_table(
                table_args.data_source,
                table_args.table_name,
                use_live_connection=self.use_live_connection,
            )
        if table_args.type == "query":
            self.check_query_reference(table_args.query_name)
            q = frappe.get_doc("Insights Query v3", table_args.query_name)
            _table = q.build(use_live_connection=self.use_live_connection, force=self.force)

        if _table is None:
            frappe.throw("Table or Query not found")

        return _table

    def get_column(self, column_name, throw=True):
        # 1. Exact match
        if column_name in self.query.columns:
            return self.query[column_name]

        # 2. Sanitized name match (handles capitalisation / special-char differences)
        if sanitize_name(column_name) in self.query.columns:
            return self.query[sanitize_name(column_name)]

        # 3. Suffix match: handles the case where a stored column name was produced
        #    in live-connection mode (e.g. "tabhd_ticket_priority_name") but the
        #    query now runs against the warehouse, where rename_duplicate_columns
        #    prepends the data-source schema prefix and produces a longer name
        #    (e.g. "support_frappe_io_tabhd_ticket_priority_name").
        #    We only match when exactly one column ends with "_{column_name}" so
        #    that ambiguous / short suffixes are never silently resolved to the
        #    wrong column.
        suffix = f"_{column_name}"
        suffix_matches = [col for col in self.query.columns if col.endswith(suffix)]
        if len(suffix_matches) == 1:
            return self.query[suffix_matches[0]]

        # 4. Schema-prefix-strip match: handles the case where a stored column name
        #    was produced in old warehouse mode (e.g. "frappe_cloud_tabinvoice_item_parent")
        #    but the query now runs without the data-source schema prefix, producing
        #    the shorter name "tabinvoice_item_parent" (new warehouse behaviour after
        #    PR #953 + revert of get_ibis_table_name).
        #    We scan all DatabaseTable nodes in the current ibis expression tree to
        #    collect the schema names that are actually present in this query, then
        #    try stripping each as a leading prefix before checking for a column match.
        all_dt = self.query.op().find_topmost(DatabaseTable)
        schemas = {
            dt.namespace.database
            for dt in all_dt
            if dt.namespace and dt.namespace.database and dt.namespace.database != "main"
        }
        for schema in schemas:
            prefix = f"{schema}_"
            if column_name.startswith(prefix):
                remainder = column_name[len(prefix) :]
                if remainder in self.query.columns:
                    return self.query[remainder]
                if sanitize_name(remainder) in self.query.columns:
                    return self.query[sanitize_name(remainder)]

        if throw:
            frappe.throw(f"Column {column_name} does not exist in the table")

    def apply_source(self, source_args):
        return self.get_table_or_query(source_args.table)

    def apply_join(self, join_args):
        right_table = self.get_right_table(join_args)
        join_condition = self.translate_join_condition(join_args, right_table)
        join_type = "outer" if join_args.join_type == "full" else join_args.join_type
        right_table = self.rename_duplicate_columns(right_table)
        return self.query.join(
            right_table,
            join_condition,
            how=join_type,
        )

    def get_right_table(self, join_args):
        right_table = self.get_table_or_query(join_args.table)

        if not join_args.select_columns:
            return right_table

        select_columns = set()

        for col in join_args.select_columns:
            select_columns.add(col.column_name)

        if join_args.join_condition and join_args.join_condition.right_column:
            select_columns.add(join_args.join_condition.right_column.column_name)

        if join_args.join_condition and join_args.join_condition.join_expression:
            expression = self.evaluate_expression(
                join_args.join_condition.join_expression.expression,
                additonal_context={
                    "t1": self.query,
                    "t2": right_table,
                },
            )
            columns_from_exp = self.get_columns_from_expression(expression)
            if columns_from_exp:
                # filter columns to only include those that exist in right_table
                columns_from_exp = [col for col in columns_from_exp if col in right_table.columns]
                select_columns.update(columns_from_exp)

        return right_table.select(select_columns)

    def get_columns_from_expression(
        self,
        expression: Expr,
        table: str | None = None,
    ):
        exp_columns = expression.op().find_topmost(Field)
        if not table:
            return list({col.name for col in exp_columns})

        columns = set()
        for col in exp_columns:
            col_table = col.rel.find_topmost(DatabaseTable)[0]
            if col_table and col_table.name == table:
                columns.add(col.name)

        return list(columns)

    def translate_join_condition(self, join_args, right_table):
        def left_eq_right_condition(left_column, right_column):
            if left_column and right_column and left_column.column_name and right_column.column_name:
                rt = right_table
                lc = self.get_column(left_column.column_name)
                rc = rt[right_column.column_name]
                return lc.cast(rc.type()) == rc

            frappe.throw("Join condition is not valid")

        join_condition = join_args.join_condition
        if join_condition.join_expression and join_condition.join_expression.expression:
            return self.evaluate_expression(
                join_condition.join_expression.expression,
                {
                    "t1": _,
                    "t2": right_table,
                },
            )
        else:
            return left_eq_right_condition(
                join_condition.left_column,
                join_condition.right_column,
            )

    def rename_duplicate_columns(self, right_table):
        query: IbisQuery = self.query
        query_columns = set(query.columns)
        right_table_columns = set(right_table.columns)
        right_table_name = get_ibis_table_name(right_table)
        right_table_name = sanitize_name(right_table_name)

        duplicate_columns = query_columns.intersection(right_table_columns)
        if not duplicate_columns:
            return right_table

        def is_conflicting(col):
            return col in query_columns or col in right_table_columns

        def get_new_name(col):
            new_name = f"{right_table_name}_{col}"
            if not is_conflicting(new_name):
                return new_name

            n = 1
            while is_conflicting(f"{new_name}_{n}"):
                n += 1
                if n > 20:
                    frappe.throw("Too many duplicate columns")

            return f"{new_name}_{n}"

        return right_table.rename(**{get_new_name(col): col for col in duplicate_columns})

    def apply_union(self, union_args):
        other_table = self.get_table_or_query(union_args.table)

        current_columns = set(self.query.columns)
        other_columns = set(other_table.columns)
        common_columns = current_columns.intersection(other_columns)

        if not common_columns:
            frappe.throw(
                "Both tables must have at least one common column to perform union",
                title="Cannot Perform Union",
            )

        # ensure columns have the same data types
        for col in common_columns:
            left_col_type = self.query.schema()[col]
            right_col_type = other_table.schema()[col]
            if left_col_type != right_col_type:
                other_table = other_table.cast({col: left_col_type})

        self.query = self.query.select(common_columns)
        other_table = other_table.select(common_columns)
        return self.query.union(other_table, distinct=union_args.distinct)

    def apply_filter(self, filter_args):
        condition = self.make_filter_condition(filter_args)
        return self.query.filter(condition)

    def make_filter_condition(self, filter_args):
        if hasattr(filter_args, "expression") and filter_args.expression:
            return self.evaluate_expression(filter_args.expression.expression)

        filter_column = filter_args.column
        filter_operator = filter_args.operator
        filter_value = filter_args.value

        left = self.get_column(filter_column.column_name)
        operator_fn = self.get_operator(filter_operator)

        if operator_fn is None:
            frappe.throw(f"Operator {filter_operator} is not supported")

        right_column = (
            self.get_column(filter_value.column_name)
            if getattr(filter_value, "column_name", None) is not None
            else None
        )

        if filter_operator in ["contains", "not_contains"]:
            filter_value = filter_value.replace("%", "")

            if left.type().is_numeric():
                left = left.cast("string")

        if filter_operator == "between":
            start = filter_value[0]
            end = filter_value[1]

            if isinstance(start, str) and isinstance(end, str):
                contains_time = ":" in start or ":" in end
                if not contains_time:
                    start = f"{start} 00:00:00"
                    end = f"{end} 23:59:59"

            filter_value = [start, end]

        right_value = right_column if right_column is not None else filter_value
        return operator_fn(left, right_value)

    def get_operator(self, operator):
        def null_check(is_null, x):
            if is_null:
                rt = x.isnull()
                if x.type().is_string():
                    rt = rt | (x == "")
            else:
                rt = x.notnull()
                if x.type().is_string():
                    rt = rt & (x != "")
            return rt

        return {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            "=": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "in": lambda x, y: x.isin(y),
            "not_in": lambda x, y: ~x.isin(y),
            "is_set": lambda x, y: null_check(False, x),
            "is_not_set": lambda x, y: null_check(True, x),
            "contains": lambda x, y: x.like(f"%{y}%"),
            "not_contains": lambda x, y: ~x.like(f"%{y}%"),
            "starts_with": lambda x, y: x.like(f"{y}%"),
            "ends_with": lambda x, y: x.like(f"%{y}"),
            "between": lambda x, y: x.between(y[0], y[1]),
            "within": lambda x, y: handle_timespan(x, y),
        }[operator]

    def apply_filter_group(self, filter_group_args):
        filters = filter_group_args.filters
        if not filters:
            return self.query

        logical_operator = filter_group_args.logical_operator
        conditions = [self.make_filter_condition(filter) for filter in filters]

        if logical_operator == "And":
            return self.query.filter(ibis.and_(*conditions))
        elif logical_operator == "Or":
            return self.query.filter(ibis.or_(*conditions))

        frappe.throw(f"Logical operator {logical_operator} is not supported")

    def apply_select(self, select_args):
        select_args = _dict(select_args)
        resolved_names = [self.get_column(col).get_name() for col in select_args.column_names]
        return self.query.select(resolved_names)

    def apply_rename(self, rename_args):
        old_name = self.get_column(rename_args.column.column_name).get_name()
        new_name = sanitize_name(rename_args.new_name)
        return self.query.rename(**{new_name: old_name})

    def apply_remove(self, remove_args):
        # Get valid columns that exist in the query
        valid_columns = []
        for column_name in remove_args.column_names:
            column = self.get_column(column_name, throw=False)
            if column is not None:
                valid_columns.append(column.get_name())

        # If no valid columns to remove, return the original query
        if not valid_columns:
            return self.query

        return self.query.drop(*valid_columns)

    def apply_cast(self, cast_args):
        col_name = self.get_column(cast_args.column.column_name).get_name()
        dtype = self.get_ibis_dtype(cast_args.data_type)
        return self.query.cast({col_name: dtype})

    def get_ibis_dtype(self, data_type):
        return {
            "String": "string",
            "Integer": "int64",
            "Decimal": "float64",
            "Date": "date",
            "Datetime": "timestamp",
            "Time": "time",
            "Text": "string",
            "JSON": "json",
            "Array": "array<json>",
            "Auto": "",
        }[data_type]

    def apply_mutate(self, mutate_args):
        new_name = sanitize_name(mutate_args.new_name)
        new_column = self.evaluate_expression(mutate_args.expression.expression)
        dtype = self.get_ibis_dtype(mutate_args.data_type)
        if dtype:
            new_column = new_column.cast(dtype)
        return self.query.mutate(**{new_name: new_column})

    def apply_sql_column(self, sql_column_args):
        """Add one column from a raw SQL expression.

        Written by the v2 migrator, for the constructs v2 expressed in SQL and v3
        has no expression for. ibis has no scalar-level SQL escape - only
        `Table.sql()` - so this is a relation-level operation and not a `mutate`.

        `new_name` is not sanitized, unlike `apply_mutate` and `apply_rename`: a
        migrated column keeps the name the v2 charts and filters already use.
        """
        new_name = sql_column_args.new_name
        raw_sql = sql_column_args.raw_sql

        if not new_name or not raw_sql or not raw_sql.strip():
            frappe.throw(
                frappe._("A SQL column needs both a name and an expression"),
            )

        if not sql_column_args.data_source:
            frappe.throw(
                frappe._("A SQL column needs the data source its expression is written for"),
            )

        data_source = frappe.get_doc("Insights Data Source v3", sql_column_args.data_source)
        source_dialect = data_source.get_sqlglot_dialect()

        raw_sql = sqlparse.format(sql=raw_sql, strip_comments=True).strip()

        alias = sg.to_identifier(new_name, quoted=True).sql(dialect=source_dialect)
        statement = f"SELECT *, {raw_sql} AS {alias} FROM {SQL_COLUMN_RELATION}"
        self._validate_sql_column_statement(statement, source_dialect)

        if not self.use_live_connection:
            statement = self._transpile_sql_to_duckdb(statement, source_dialect)

        # the alias is what puts the current pipeline in scope: without it ibis emits
        # `FROM <original table>` and any column derived mid-pipeline is unresolvable
        query = self.query.alias(SQL_COLUMN_RELATION).sql(statement)

        dtype = self.get_ibis_dtype(sql_column_args.data_type) if sql_column_args.data_type else None
        return query.cast({new_name: dtype}) if dtype else query

    def _validate_sql_column_statement(self, statement: str, dialect: str) -> None:
        """Validate the assembled statement, not the expression alone.

        An expression parsed on its own is read as the start of a statement, so
        `replace(...)` reads as MySQL's REPLACE. In place, it is one projection.
        """
        try:
            parsed = sg.parse(statement, dialect=dialect)
        except Exception as e:
            frappe.throw(
                frappe._("Failed to parse the SQL column expression: {0}").format(e),
            )

        if len(parsed) != 1 or not isinstance(parsed[0], sg.exp.Select):
            frappe.throw(
                frappe._("A SQL column expression must be a single expression"),
            )

        select = parsed[0]
        tables = {table.name for table in select.find_all(sg.exp.Table)}
        nested = len(list(select.find_all(sg.exp.Select))) > 1 or select.find(sg.exp.Subquery)
        if nested or tables != {SQL_COLUMN_RELATION}:
            frappe.throw(
                frappe._("A SQL column expression cannot read another table"),
            )

    def apply_summary(self, summarize_args):
        aggregates = [self.translate_measure(measure) for measure in summarize_args.measures]
        aggregates = {agg.get_name(): agg for agg in aggregates}
        group_bys = [self.translate_dimension(dimension) for dimension in summarize_args.dimensions]
        return self.query.aggregate(**aggregates, by=group_bys)

    def apply_order_by(self, order_by_args):
        order_by_column = self.get_column(order_by_args.column.column_name, throw=False)
        if order_by_column is None:
            return self.query
        order_fn = ibis.asc if order_by_args.direction == "asc" else ibis.desc
        return self.query.order_by(order_fn(order_by_column))

    def apply_limit(self, limit_args):
        limit = clamp(limit_args.limit, 1, 10_00_000)
        return self.query.limit(limit)

    def apply_pivot(self, pivot_args, pivot_type):
        rows = [self.translate_dimension(dimension) for dimension in pivot_args["rows"]]
        columns = [self.translate_dimension(dimension) for dimension in pivot_args["columns"]]
        values = [self.translate_measure(measure) for measure in pivot_args["values"]]

        if pivot_type == "wider":
            self.query = self.query.group_by(*rows, *columns).aggregate(
                **{value.get_name(): value for value in values}
            )

            date_dimensions = [
                self.translate_dimension(dim).get_name()
                for dim in pivot_args["columns"]
                if self.is_date_type(dim.data_type)
            ]
            if date_dimensions:
                self.query = self.query.cast({dimension: "string" for dimension in date_dimensions})

            names_from = [col.get_name() for col in columns]
            max_names = pivot_args.get("max_column_values", 10)
            max_names = int(max_names)
            max_names = max(1, min(max_names, 100))
            value_names = [value.get_name() for value in values]
            names, has_tail = self.get_top_pivot_names(names_from, value_names, max_names)

            # If we've limited the number of distinct column values, bucket the
            # remaining values into an "Others" group so charts show the rest.
            # This currently supports the common case of a single pivot column.
            if has_tail and len(columns) == 1:
                selected_names = [str(v) for v in names.flatten()]

                col_name = columns[0].get_name()
                col_expr = getattr(self.query, col_name)

                # replace values not in selected_names with 'Others'
                # use ibis.case() since ibis.where isn't available on the module
                others_expr = ibis.cases((col_expr.isin(selected_names), col_expr), else_="Others")
                self.query = self.query.mutate(**{col_name: others_expr})

                # ensure the pivot names include the 'Others' bucket
                names = list(map(str, selected_names))
                names.append("Others")

            return self.query.pivot_wider(
                id_cols=[row.get_name() for row in rows],
                names_from=names_from,
                names_sep="___",
                names=names,
                values_from=[value.get_name() for value in values],
                values_agg="sum",
            )

        return self.query

    def get_top_pivot_names(self, names_from, value_names, max_names):
        """The distinct column values a pivot keeps, and whether it cut any.

        Everything the cut leaves out lands in "Others", so this ranking decides
        which series a chart draws. Rank by the measure, not by the value's own
        name: alphabetical order buries the largest series in the tail. Several
        measures rank by the first. With none, the pivot only shows which groups
        exist, so the number of rows ranks them.

        The names come back in their own ascending order, which becomes the
        column order. A split on a date stays chronological that way.
        """
        rank = getattr(self.query, value_names[0]).sum() if value_names else self.query.count()
        ranked = self.query.aggregate(**{"__rank__": rank}, by=names_from)
        # names_from breaks a tie, so an equal measure keeps the same set every run
        ranked = ranked.order_by([ibis.desc("__rank__"), *names_from])
        # one past the cap tells a real cut apart from a set that just fits, which
        # keeps an empty "Others" column out of the result
        ranked = ranked.limit(max_names + 1)

        top = ranked.execute()
        has_tail = len(top) > max_names
        top = top.head(max_names).sort_values(names_from, na_position="last")
        return top[names_from].fillna("null").values, has_tail

    def apply_custom_operation(self, operation):
        return self.evaluate_expression(operation.expression.expression)

    def apply_sql(self, sql_args):
        data_source = sql_args.data_source
        raw_sql = sql_args.raw_sql

        ds = frappe.get_doc("Insights Data Source v3", data_source)
        db = ds._get_ibis_backend() if self.use_live_connection else insights.warehouse.db
        source_dialect = ds.get_sqlglot_dialect()

        raw_sql = sqlparse.format(sql=raw_sql, strip_comments=True)
        raw_sql = self._validate_native_sql(raw_sql, use_live_connection=self.use_live_connection)

        check_permissions = frappe.db.get_single_value(
            "Insights Settings", "enable_permissions"
        ) or frappe.db.get_single_value("Insights Settings", "apply_user_permissions")

        if check_permissions or not self.use_live_connection:
            tables = self._get_sql_table_names(
                raw_sql,
                dialect=source_dialect,
                use_live_connection=self.use_live_connection,
            )
            replace_map = self._get_sql_table_bindings(
                data_source,
                tables,
                dialect=source_dialect,
                use_live_connection=self.use_live_connection,
                check_permissions=check_permissions,
            )

            if not self.use_live_connection:
                raw_sql = self._transpile_sql_to_duckdb(raw_sql, source_dialect)

            raw_sql = self._prepend_sql_with_clauses(raw_sql, replace_map)

        supports_stored_procedure = ds.database_type in ["PostgreSQL", "MSSQL", "MariaDB"]
        if (
            supports_stored_procedure
            and ds.enable_stored_procedure_execution
            and raw_sql.strip().lower().startswith("exec")
        ):
            current_date = date.today().strftime("%Y-%m-%d")  # Format: 'YYYY-MM-DD'
            raw_sql = raw_sql.replace("@Today", f"'{current_date}'")

            result = db.raw_sql(raw_sql)

            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            df = pd.DataFrame.from_records(rows, columns=columns)

            results = ibis.memtable(df)

        elif raw_sql.strip().lower().startswith(("select", "with")):
            results = db.sql(raw_sql)

        else:
            frappe.throw(
                "SQL query must start with a SELECT or WITH statement",
                title="Invalid SQL Query",
            )

        return results

    def _validate_native_sql(self, raw_sql: str, use_live_connection: bool) -> str:
        raw_sql = raw_sql.strip()

        if not use_live_connection:
            statements = [stmt for stmt in sqlparse.parse(raw_sql) if stmt.tokens and stmt.value.strip()]
            if len(statements) > 1:
                frappe.throw(
                    "Multiple SQL statements are not supported with Data Store for native queries",
                    title="Unsupported SQL Query",
                )

            if raw_sql.lower().startswith("exec"):
                frappe.throw(
                    "Stored procedures are not supported with Data Store for native queries",
                    title="Unsupported SQL Query",
                )

        return raw_sql

    def _transpile_sql_to_duckdb(self, raw_sql: str, source_dialect: str | None) -> str:
        if not source_dialect or source_dialect == "duckdb":
            return raw_sql

        try:
            transpiled_sql = sg.transpile(raw_sql, read=source_dialect, write="duckdb")
        except Exception as e:
            frappe.throw(
                f"Failed to translate SQL query for Data Store execution: {e}",
                title="Unsupported SQL Query",
            )

        if not transpiled_sql:
            frappe.throw(
                "Failed to translate SQL query for Data Store execution",
                title="Unsupported SQL Query",
            )

        return transpiled_sql[0]

    def _get_sql_table_names(
        self,
        raw_sql: str,
        dialect: sg.Dialect | None,
        use_live_connection: bool,
    ) -> set[str]:
        tables = set()
        for table_ref in extract_sql_table_refs(raw_sql, dialect=dialect):
            if not use_live_connection and (table_ref.db or table_ref.catalog):
                frappe.throw(
                    "Schema-qualified table names are not supported with Data Store for native queries yet",
                    title="Unsupported SQL Query",
                )

            tables.add(table_ref.name)

        return tables

    def _get_sql_table_bindings(
        self,
        data_source: str,
        tables: set[str],
        dialect: sg.Dialect | None,
        use_live_connection: bool,
        check_permissions: bool,
    ) -> dict[str, str]:
        replace_map = {}

        for table_name in tables:
            table_expr = InsightsTablev3.get_ibis_table(
                data_source,
                table_name,
                use_live_connection=use_live_connection,
            )
            table_sql = ibis.to_sql(table_expr)

            if use_live_connection and check_permissions:
                table_sql_parsed = sg.parse_one(table_sql, dialect=dialect)
                if not table_sql_parsed.find(sg.exp.Where):
                    # if we are running in live connection and there are no permission filters applied,
                    # we skip replacing the table with a subquery
                    continue

            replace_map[table_name] = table_sql

        return replace_map

    def _prepend_sql_with_clauses(self, raw_sql: str, replace_map: dict[str, str]) -> str:
        if not replace_map:
            return raw_sql

        with_clauses = []
        for table_name, table_sql in replace_map.items():
            quoted_table_name = sg.to_identifier(table_name)
            with_clauses.append(f"{quoted_table_name} AS ({table_sql})")

        with_clause_sql = ", ".join(with_clauses)
        raw_sql_stripped = raw_sql.strip()
        if raw_sql_stripped.lower().startswith("with"):
            return re.sub(
                r"(\bwith\b)",
                f"WITH {with_clause_sql},",
                raw_sql_stripped,
                count=1,
                flags=re.IGNORECASE,
            )

        return f"WITH {with_clause_sql} {raw_sql_stripped}"

    def apply_code(self, code_args):
        code = code_args.code

        adhoc_filters = frappe.as_json(getattr(frappe.local, "insights_adhoc_filters", {}))
        variables = resolve_variables(getattr(self.doc, "variables", None))
        # a variable value changes the output as surely as the code does, so it
        # belongs in the key that decides whether the script runs again
        digest = make_digest(code, adhoc_filters, frappe.as_json(variables))

        cached_results = None if self.force else get_cached_results(digest)
        if cached_results is not None:
            results = cached_results
        else:
            results = get_code_results(code, variables=variables)
            cache_results(digest, results, cache_expiry=60 * 5)

        # DuckDB (via PyArrow) cannot create tables with NULL-typed columns.
        # PyArrow infers pa.null() for any all-None column regardless of pandas dtype.
        # Casting to pandas StringDtype makes PyArrow emit pa.large_string() instead,
        # which DuckDB accepts while still preserving null values as pd.NA.
        for col in results.columns:
            if results[col].isna().all():
                results[col] = results[col].astype(pd.StringDtype())

        return insights.warehouse.db.create_table(
            digest,
            results,
            temp=True,
            overwrite=True,
        )

    def translate_measure(self, measure):
        if measure.column_name == "count" and measure.aggregation == "count":
            first_column = self.query.columns[0]
            first_column = getattr(self.query, first_column)
            return first_column.count().name(measure.measure_name)

        if "expression" in measure:
            column = self.evaluate_expression(measure.expression.expression)
            dtype = self.get_ibis_dtype(measure.data_type)
            column = column.cast(dtype)
        else:
            column = self.get_column(measure.column_name)
            column = self.apply_aggregate(column, measure.aggregation)

        return column.name(measure.measure_name)

    def translate_dimension(self, dimension):
        col = self.get_column(dimension.column_name)

        if dimension.windows:
            col = self.apply_windows(col, dimension.windows)
            dtype = self.get_ibis_dtype(dimension.data_type)
            if dtype:
                col = col.cast(dtype)
            return col.name(dimension.dimension_name or dimension.column_name)

        if dimension.data_type == "Time" and dimension.granularity:
            col = self.apply_time_granularity(col, dimension.granularity)
            return col.name(dimension.dimension_name or dimension.column_name)

        if self.is_date_type(dimension.data_type) and dimension.granularity:
            col = self.apply_granularity(col, dimension.granularity, dimension.data_type)
            col = col.cast(self.get_ibis_dtype(dimension.data_type))
        return col.name(dimension.dimension_name or dimension.column_name)

    def apply_windows(self, column, windows):
        """The window a row falls in, named by the date that window starts on.

        A card grouped by this gets one row per window whatever its span covers,
        and the start dates sort the windows oldest first — the order a number
        card reads its rows in. A span carries no dates until here, because the
        clock and the fiscal calendar are only known while the query runs.

        A row is labelled by the oldest window holding it, so two windows that
        overlap never count it twice. A row outside every window is labelled
        nothing, and the filter beside the group-by keeps it out of the result.
        """
        branches = []
        for start, end in sorted({resolve_timespan(window) for window in windows}):
            bounds = add_start_and_end_time([start, end])
            branches.append((column.between(*bounds), ibis.literal(start)))

        return ibis.cases(*branches)

    def is_date_type(self, data_type):
        return data_type in ["Date", "Datetime", "Time"]

    def apply_aggregate(self, column, aggregate_function):
        if aggregate_function == "count_distinct":
            return column.nunique()
        if aggregate_function == "count":
            return column.count()
        if aggregate_function == "sum":
            return column.sum()
        if aggregate_function == "avg":
            return column.mean()
        if aggregate_function == "min":
            return column.min()
        if aggregate_function == "max":
            return column.max()

        frappe.throw(f"Aggregate function {aggregate_function} is not supported")

    def apply_granularity(self, column, granularity, data_type=None):
        supported_granularities = [
            "second",
            "minute",
            "hour",
            "day",
            "week",
            "month",
            "quarter",
            "year",
            "fiscal_year",
        ]
        if granularity not in supported_granularities:
            supported = ", ".join(supported_granularities)
            frappe.throw(
                f"Granularity {granularity} is not supported for {data_type} columns. Supported granularities: {supported}",
                title="Unsupported Granularity",
            )

        if granularity == "week":
            return week_start(column).name(column.get_name())
        if granularity == "fiscal_year":
            return fiscal_year_start(column).name(column.get_name())

        truncate_unit = {
            "second": "s",
            "minute": "m",
            "hour": "h",
            "day": "D",
            "quarter": "Q",
            "month": "M",
            "year": "Y",
        }
        if granularity not in truncate_unit:
            frappe.throw(f"Granularity {granularity} is not supported")
        return column.truncate(truncate_unit[granularity]).name(column.get_name())

    def apply_time_granularity(self, column, granularity):
        supported_granularities = ["second", "minute", "hour"]
        if granularity not in supported_granularities:
            supported = ", ".join(supported_granularities)
            frappe.throw(
                f"Granularity {granularity} is not supported for Time columns. Supported granularities: {supported}",
                title="Unsupported Granularity",
            )

        time_string = column.cast("string")
        if granularity == "hour":
            return time_string.substr(0, 2).concat(ibis.literal(":00:00"))
        if granularity == "minute":
            return time_string.substr(0, 5).concat(ibis.literal(":00"))
        if granularity == "second":
            return time_string.substr(0, 8)

        frappe.throw(f"Granularity {granularity} is not supported for Time columns")

    def evaluate_expression(self, expression, additonal_context=None):
        if not expression or not expression.strip():
            raise ValueError(f"Invalid expression: {expression}")

        frappe.flags.current_ibis_query = self.query
        context = frappe._dict()
        context.pandas = frappe._dict()
        context.pandas.DataFrame = SafePandasDataFrame
        context.q = self.query
        context.update(self.get_current_columns())
        context.update(get_functions())
        context.update(additonal_context or {})
        ret = exec_with_return(expression, context)
        frappe.flags.current_ibis_query = None
        return ret

    def get_current_columns(self):
        # TODO: handle collisions with function names
        return {col: getattr(self.query, col) for col in self.query.schema().names}


def clamp(value, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return lo


def execute_ibis_query(
    query: IbisQuery,
    page=1,
    page_size=100,
    paginate=True,
    force=False,
    cache=True,
    cache_expiry=3600,
    reference_doctype=None,
    reference_name=None,
):
    if paginate and hasattr(query, "limit"):
        page_size = clamp(page_size, 1, 10_000)
        page = clamp(page, 1, 10_000)
        offset = (page - 1) * page_size
        query = query.limit(page_size, offset=offset)

    try:
        sql = ibis.to_sql(query)
    except ibis.common.exceptions.OperationNotDefinedError:
        # TODO: throw better error message
        raise

    backend = query.get_backend()
    if cache:
        backend_id = backend.db_identity if backend else None
        cache_key = make_digest(sql, backend_id)

        if has_cached_results(cache_key) and not force:
            return get_cached_results(cache_key), -1

    time_taken = -1
    use_data_store = is_warehouse(backend)

    try:
        if use_data_store:
            start = time.monotonic()
            result = query.execute()
            time_taken = flt(time.monotonic() - start, 3)
        else:
            result, time_taken = _execute_live_query(query)
    except Exception as e:
        if "max_statement_time" in str(e):
            frappe.log_error(
                title="Query execution time exceeded the limit.",
                message=f"Query: {sql}",
            )
            from insights.insights.doctype.insights_settings.insights_settings import (
                get_max_execution_time,
            )

            max_time = get_max_execution_time()
            frappe.throw(
                title="Query Timeout",
                msg=f"Query execution time exceeded the limit of {max_time} seconds. Please try again with a smaller timespan or a more specific filter.",
            )
        raise e

    create_execution_log(
        sql,
        time_taken,
        query_name=reference_name,
        data_store=use_data_store,
    )

    if isinstance(result, pd.DataFrame):
        result = result.replace({pd.NaT: None, np.nan: None})
        if cache:
            cache_results(cache_key, result, cache_expiry)

    return result, time_taken


# reject immediately instead of waiting for a slot: a blocked request holds on to a
# web thread, so waiting here is what starves the pool when a dashboard executes all
# of its charts at once. The frontend retries on the 503.
@concurrent_limit(wait_timeout=0)
def _execute_live_query(query: IbisQuery):
    start = time.monotonic()
    result = query.execute()
    return result, flt(time.monotonic() - start, 3)


def get_columns_from_schema(schema: ibis.Schema):
    return [
        {
            "name": col,
            "type": to_insights_type(dtype),
        }
        for col, dtype in schema.items()
    ]


def to_insights_type(dtype: DataType):
    if dtype.is_string():
        return "String"
    if dtype.is_integer():
        return "Integer"
    if dtype.is_floating():
        return "Decimal"
    if dtype.is_decimal():
        return "Decimal"
    if dtype.is_timestamp():
        return "Datetime"
    if dtype.is_date():
        return "Date"
    if dtype.is_time():
        return "Time"
    if dtype.is_json():
        return "JSON"
    if dtype.is_array():
        return "Array"
    return "String"


def _results_cache_key(cache_key):
    # v2 stores the column names alongside the rows, so the prefix change drops
    # the v1 entries that cannot be read back with their schema intact
    return "insights:query_results:v2:" + cache_key


def cache_results(cache_key, result: pd.DataFrame, cache_expiry=3600):
    payload = {
        "columns": list(result.columns),
        "rows": result.to_dict(orient="records"),
    }
    frappe.cache().set_value(
        _results_cache_key(cache_key),
        frappe.as_json(payload),
        expires_in_sec=cache_expiry,
    )


def get_cached_results(cache_key) -> pd.DataFrame:
    data = frappe.cache().get_value(_results_cache_key(cache_key))
    if not data:
        return None
    payload = frappe.parse_json(data)
    # a result with no rows still has columns, and records alone cannot carry them
    df = pd.DataFrame(payload["rows"], columns=payload["columns"])
    return df.replace({pd.NaT: None, np.nan: None})


def has_cached_results(cache_key):
    return frappe.cache().get_value(_results_cache_key(cache_key)) is not None


def exec_with_return(
    script: str,
    _globals: dict | None = None,
    _locals: dict | None = None,
):
    assert_expression_has_no_io(script)

    tree = ast.parse(script)

    if not tree.body:
        raise ValueError("Empty code")

    output_expression = script

    last_node = tree.body[-1]
    if isinstance(last_node, ast.Expr):
        output_expression = ast.unparse(last_node)
    elif isinstance(last_node, ast.Assign):
        output_expression = ast.unparse(last_node.value)
    elif isinstance(last_node, ast.AnnAssign | ast.AugAssign):
        output_expression = ast.unparse(last_node.value)

    _globals = _globals or {}
    _locals = _locals or {}

    tree.body.pop()  # remove the last expression
    _script = ast.unparse(tree)
    if _script.strip():
        with ensure_rollback():
            safe_exec(_script, _globals, _locals, restrict_commit_rollback=True)
        return safe_eval(output_expression, _globals, _locals)
    else:
        return safe_eval(output_expression, _globals, _locals)


def get_ibis_table_name(table: IbisQuery):
    dt = table.op().find_topmost(DatabaseTable)
    if not dt:
        return "right_table"
    return dt[0].name


def sanitize_name(name):
    if not name:
        return name
    return (
        name.strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
        .replace("(", "_")
        .replace(")", "_")
        .lower()
    )


class SafePandasDataFrame(pd.DataFrame):
    def to_csv(self, *args, **kwargs):
        raise NotImplementedError("to_csv is not supported in this context")

    def to_json(self, *args, **kwargs):
        raise NotImplementedError("to_json is not supported in this context")


def publish_script_logs():
    # this runs in a finally, so an unguarded raise here would replace the
    # script's own exception - or its result - with a realtime transport error
    try:
        frappe.publish_realtime(
            event="insights_script_log",
            user=frappe.session.user,
            message={
                "user": frappe.session.user,
                "logs": frappe.debug_log,
            },
        )
    except Exception:
        frappe.log_error("Failed to publish script query logs")


def format_script_error(code: str) -> str:
    exc_type, exc_value, tb = sys.exc_info()
    name = getattr(exc_type, "__name__", "Error")
    message = f"{name}: {exc_value}"

    lineno = get_script_line_number(exc_value, tb)
    if not lineno:
        return message

    lines = code.splitlines()
    source = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
    return f"Line {lineno}: {source}\n{message}" if source else f"Line {lineno}\n{message}"


def get_script_line_number(exc_value, tb) -> int | None:
    # RestrictedPython compiles the script under this filename, so its frames are
    # the only ones with a line number that means anything to the author
    for frame in traceback.extract_tb(tb):
        if frame.filename.startswith(SERVER_SCRIPT_FILE_PREFIX):
            return frame.lineno

    # a syntax error never runs, so it has no frame of its own
    if isinstance(exc_value, SyntaxError):
        return exc_value.lineno

    return None


def resolve_variables(variables) -> dict:
    if not variables:
        return {}

    from frappe.utils.password import get_decrypted_password

    resolved = {}
    for var in variables:
        if isinstance(var, dict):
            resolved[var.get("variable_name")] = var.get("variable_value")
        else:
            resolved[var.variable_name] = get_decrypted_password(var.doctype, var.name, "variable_value")
    return resolved


def get_code_results(code: str, variables: dict | None = None):
    pandas = frappe._dict()
    pandas.DataFrame = SafePandasDataFrame
    pandas.read_csv = pd.read_csv
    pandas.json_normalize = pd.json_normalize

    results = []
    frappe.local.debug_log = []

    _locals = {"results": results, **(variables or {})}
    start = time.monotonic()
    try:
        with ensure_rollback():
            _, _locals = safe_exec(
                code,
                _globals={"pandas": pandas},
                _locals=_locals,
                restrict_commit_rollback=True,
            )
    except Exception:
        # the panel is the only place the script author sees anything, so the
        # error has to land there before it travels on as a request failure
        frappe.log(format_script_error(code))
        raise
    else:
        results = to_dataframe(_locals["results"])
        frappe.log(f"{len(results)} rows in {flt(time.monotonic() - start, 3)}s")
        return results
    finally:
        publish_script_logs()


def to_dataframe(results) -> pd.DataFrame:
    if isinstance(results, pd.DataFrame):
        return results

    if results is None or len(results) == 0:
        # DuckDB cannot hold a table with no columns, so an empty run still needs
        # one. A named column beats the fake row of errors this used to return.
        return pd.DataFrame({"results": pd.Series([], dtype="string")})

    try:
        if isinstance(results, list) and isinstance(results[0], list | tuple):
            return pd.DataFrame.from_records(results)
        return pd.DataFrame(results)
    except (ValueError, TypeError):
        import json as _json

        return pd.DataFrame(_json.loads(frappe.as_json(results)))


@contextmanager
def ensure_rollback():
    hash = frappe.generate_hash(length=4)
    try:
        frappe.db.savepoint(f"save_point_{hash}")
        yield
    finally:
        frappe.db.rollback(save_point=f"save_point_{hash}")
