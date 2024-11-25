import ast
import time

import frappe
import ibis
import numpy as np
import pandas as pd
from frappe.utils.data import flt
from frappe.utils.safe_exec import safe_eval, safe_exec
from ibis import _
from ibis.expr.datatypes import DataType
from ibis.expr.operations.relations import DatabaseTable, Field
from ibis.expr.types import Expr
from ibis.expr.types import Table as IbisQuery

from insights.cache_utils import make_digest
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    InsightsTablev3,
)
from insights.insights.query_builders.sql_functions import handle_timespan
from insights.utils import create_execution_log
from insights.utils import deep_convert_dict_to_dict as _dict

from .ibis_functions import get_functions


class IbisQueryBuilder:
    def build(self, operations: list, use_live_connection=True) -> IbisQuery:
        self.query = None
        self.use_live_connection = use_live_connection
        for idx, operation in enumerate(operations):
            try:
                operation = _dict(operation)
                self.query = self.perform_operation(operation)
            except frappe.exceptions.ValidationError as e:
                raise e
            except Exception as e:
                operation_type_title = frappe.bold(operation.type.title())
                frappe.throw(
                    f"Invalid {operation_type_title} Operation at position {idx + 1}: {e!s}"
                )
        return self.query

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
        return self.query

    def get_table_or_query(self, table_args):
        _table = None

        if table_args.type == "table":
            _table = InsightsTablev3.get_ibis_table(
                table_args.data_source,
                table_args.table_name,
                use_live_connection=self.use_live_connection,
            )
        if table_args.type == "query":
            _table = IbisQueryBuilder().build(
                table_args.operations,
                use_live_connection=self.use_live_connection,
            )

        if _table is None:
            frappe.throw("Invalid join table")

        return _table

    def get_column(self, column_name, throw=True):
        if column_name in self.query.columns:
            return getattr(self.query, column_name)
        if sanitize_name(column_name) in self.query.columns:
            return getattr(self.query, sanitize_name(column_name))
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
            right_table_columns = self.get_columns_from_expression(
                expression, table=join_args.table.table_name
            )
            select_columns.update(right_table_columns)

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
            if (
                left_column
                and right_column
                and left_column.column_name
                and right_column.column_name
            ):
                rt = right_table
                lc = getattr(self.query, left_column.column_name)
                rc = getattr(rt, right_column.column_name)
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

        return right_table.rename(
            **{get_new_name(col): col for col in duplicate_columns}
        )

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
            if hasattr(filter_value, "column_name")
            else None
        )

        right_value = right_column or filter_value
        return operator_fn(left, right_value)

    def get_operator(self, operator):
        return {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            "=": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "in": lambda x, y: x.isin(y),
            "not_in": lambda x, y: ~x.isin(y),
            "is_set": lambda x, y: (x.notnull()) & (x != ""),
            "is_not_set": lambda x, y: (x.isnull()) | (x == ""),
            "contains": lambda x, y: x.like(y),
            "not_contains": lambda x, y: ~x.like(y),
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
        return self.query.select(select_args.column_names)

    def apply_rename(self, rename_args):
        old_name = self.get_column(rename_args.column.column_name).get_name()
        new_name = sanitize_name(rename_args.new_name)
        return self.query.rename(**{new_name: old_name})

    def apply_remove(self, remove_args):
        to_remove = {self.get_column(col) for col in remove_args.column_names}
        to_remove = {col.get_name() for col in to_remove}
        return self.query.drop(*to_remove)

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
        }[data_type]

    def apply_mutate(self, mutate_args):
        new_name = sanitize_name(mutate_args.new_name)
        dtype = self.get_ibis_dtype(mutate_args.data_type)
        new_column = self.evaluate_expression(mutate_args.expression.expression)
        new_column = new_column.cast(dtype)
        return self.query.mutate(**{new_name: new_column})

    def apply_summary(self, summarize_args):
        aggregates = [
            self.translate_measure(measure) for measure in summarize_args.measures
        ]
        aggregates = {agg.get_name(): agg for agg in aggregates}
        group_bys = [
            self.translate_dimension(dimension)
            for dimension in summarize_args.dimensions
        ]
        return self.query.aggregate(**aggregates, by=group_bys)

    def apply_order_by(self, order_by_args):
        order_by_column = self.get_column(order_by_args.column.column_name, throw=False)
        if order_by_column is None:
            return self.query
        order_fn = ibis.asc if order_by_args.direction == "asc" else ibis.desc
        return self.query.order_by(order_fn(order_by_column))

    def apply_limit(self, limit_args):
        return self.query.limit(int(limit_args.limit))

    def apply_pivot(self, pivot_args, pivot_type):
        rows = [self.translate_dimension(dimension) for dimension in pivot_args["rows"]]
        columns = [
            self.translate_dimension(dimension) for dimension in pivot_args["columns"]
        ]
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
                self.query = self.query.cast(
                    {dimension: "string" for dimension in date_dimensions}
                )

            names_from = [col.get_name() for col in columns]
            names = (
                self.query.select(names_from)
                .order_by(names_from)
                .distinct()
                .limit(10)
                .execute()
            )
            names = names.fillna("null").values

            return self.query.pivot_wider(
                id_cols=[row.get_name() for row in rows],
                names_from=names_from,
                names_sep="___",
                names=names,
                values_from=[value.get_name() for value in values],
                values_agg="sum",
            )

        return self.query

    def apply_custom_operation(self, operation):
        return self.evaluate_expression(operation.expression.expression)

    def apply_sql(self, sql_args):
        data_source = sql_args.data_source
        raw_sql = sql_args.raw_sql

        if not raw_sql.strip().lower().startswith(("select", "with")):
            frappe.throw(
                "SQL query must start with a SELECT or WITH statement",
                title="Invalid SQL Query",
            )

        ds = frappe.get_doc("Insights Data Source v3", data_source)
        db = ds._get_ibis_backend()
        return db.sql(raw_sql)

    def apply_code(self, code_args):
        code = code_args.code

        pandas = frappe._dict()
        pandas.DataFrame = pd.DataFrame
        pandas.read_csv = pd.read_csv
        pandas.json_normalize = pd.json_normalize
        # prevent users from writing to disk
        pandas.DataFrame.to_csv = lambda *args, **kwargs: None
        pandas.DataFrame.to_json = lambda *args, **kwargs: None

        results = []
        _, _locals = safe_exec(
            code,
            _globals={"pandas": pandas},
            _locals={"results": results},
            restrict_commit_rollback=True,
        )
        results = _locals["results"]
        if results is None or len(results) == 0:
            results = [{"error": "No results"}]

        frappe.publish_realtime(
            event="insights_script_log",
            user=frappe.session.user,
            message={
                "user": frappe.session.user,
                "logs": frappe.debug_log,
            },
        )

        return ibis.memtable(results, name=make_digest(code))

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
        col = getattr(self.query, dimension.column_name)
        if self.is_date_type(dimension.data_type) and dimension.granularity:
            col = self.apply_granularity(col, dimension.granularity)
            col = col.cast(self.get_ibis_dtype(dimension.data_type))
        return col.name(dimension.dimension_name or dimension.column_name)

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

    def apply_granularity(self, column, granularity):
        if granularity == "week":
            week_start_day = (
                frappe.db.get_single_value("Insights Settings", "week_starts_on")
                or "Monday"
            )
            days = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            week_starts_on = days.index(week_start_day)
            day_of_week = column.day_of_week.index().cast("int32")
            adjusted_week_start = (day_of_week - week_starts_on + 7) % 7
            week_start = column - adjusted_week_start.to_interval(unit="D")
            return week_start.strftime("%Y-%m-%d").name(column.get_name())
        if granularity == "quarter":
            year = column.year()
            quarter = column.quarter()
            month = (quarter * 3) - 2
            quarter_start = ibis.date(year, month, 1)
            return quarter_start.strftime("%Y-%m-%d").name(column.get_name())

        format_str = {
            "day": "%Y-%m-%d",
            "month": "%Y-%m-01",
            "year": "%Y-01-01",
        }
        if not format_str.get(granularity):
            frappe.throw(f"Granularity {granularity} is not supported")
        return column.strftime(format_str[granularity]).name(column.get_name())

    def evaluate_expression(self, expression, additonal_context=None):
        if not expression or not expression.strip():
            raise ValueError(f"Invalid expression: {expression}")

        frappe.flags.current_ibis_query = self.query
        context = frappe._dict()
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


def execute_ibis_query(
    query: IbisQuery, limit=100, cache=True, cache_expiry=3600
) -> pd.DataFrame:
    limit = int(limit or 100)
    limit = min(max(limit, 1), 10_00_000)
    query = query.head(limit) if limit else query
    sql = ibis.to_sql(query)
    cache_key = make_digest(sql, query._find_backend().db_identity)

    if cache and has_cached_results(cache_key):
        return get_cached_results(cache_key), -1

    start = time.monotonic()
    result: pd.DataFrame = query.execute()
    time_taken = flt(time.monotonic() - start, 3)
    create_execution_log(sql, time_taken)

    result = result.replace({pd.NaT: None, np.nan: None})

    if cache:
        cache_results(cache_key, result, cache_expiry)

    return result, time_taken


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
    return "String"


def cache_results(cache_key, result: pd.DataFrame, cache_expiry=3600):
    cache_key = "insights:query_results:" + cache_key
    data = result.to_dict(orient="records")
    data = frappe.as_json(data)
    frappe.cache().set_value(cache_key, data, expires_in_sec=cache_expiry)


def get_cached_results(cache_key) -> pd.DataFrame:
    cache_key = "insights:query_results:" + cache_key
    data = frappe.cache().get_value(cache_key)
    if not data:
        return None
    data = frappe.parse_json(data)
    df = pd.DataFrame(data).replace({pd.NaT: None, np.nan: None})
    return df


def has_cached_results(cache_key):
    cache_key = "insights:query_results:" + cache_key
    return frappe.cache().get_value(cache_key) is not None


def exec_with_return(
    code: str,
    _globals: dict | None = None,
    _locals: dict | None = None,
):
    a = ast.parse(code)

    last_expression = None
    if a.body:
        if isinstance(a_last := a.body[-1], ast.Expr):
            last_expression = ast.unparse(a.body.pop())
        elif isinstance(a_last, ast.Assign):
            last_expression = ast.unparse(a_last.targets[0])
        elif isinstance(a_last, ast.AnnAssign | ast.AugAssign):
            last_expression = ast.unparse(a_last.target)

    _globals = _globals or {}
    _locals = _locals or {}
    if last_expression:
        safe_exec(ast.unparse(a), _globals, _locals, restrict_commit_rollback=True)
        return safe_eval(last_expression, _globals, _locals)
    else:
        return safe_eval(code, _globals, _locals)


def get_ibis_table_name(table: IbisQuery):
    dt = table.op().find_topmost(DatabaseTable)
    if not dt:
        return None
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
