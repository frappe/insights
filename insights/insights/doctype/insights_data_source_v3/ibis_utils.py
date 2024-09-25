import ast
import time

import frappe
import ibis
import numpy as np
import pandas as pd
from frappe.utils.data import flt
from frappe.utils.safe_exec import safe_eval, safe_exec
from ibis import _
from ibis import selectors as s
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
        for operation in operations:
            self.query = self.perform_operation(operation)
        return self.query

    def get_table(self, table):
        return InsightsTablev3.get_ibis_table(
            table.data_source,
            table.table_name,
            use_live_connection=self.use_live_connection,
        )

    def perform_operation(self, operation):
        operation = _dict(operation)
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
        return self.query

    def apply_source(self, source_args):
        return self.get_table(source_args.table)

    def apply_join(self, join_args):
        right_table = self.get_right_table(join_args)
        join_condition = self.translate_join_condition(join_args, right_table)
        join_type = "outer" if join_args.join_type == "full" else join_args.join_type
        return self.query.join(
            right_table,
            join_condition,
            how=join_type,
        ).select(~s.endswith("right"))

    def get_table_or_query(self, table_args):
        _table = None

        if table_args.type == "table":
            _table = self.get_table(table_args)
        if table_args.type == "query":
            _table = IbisQueryBuilder().build(
                table_args.operations,
                use_live_connection=self.use_live_connection,
            )

        if _table is None:
            frappe.throw("Invalid join table")

        return _table

    def get_right_table(self, join_args):
        right_table = self.get_table_or_query(join_args.table)

        if not join_args.select_columns:
            return right_table

        select_columns = [col.column_name for col in join_args.select_columns]

        if join_args.right_column:
            select_columns.append(join_args.right_column.column_name)

        if join_args.join_condition and join_args.join_condition.right_column:
            select_columns.append(join_args.join_condition.right_column.column_name)

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
            select_columns.extend(right_table_columns)

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
                lc = getattr(_, left_column.column_name)
                rc = getattr(rt, right_column.column_name)
                return lc.cast(rc.type()) == rc

            frappe.throw("Join condition is not valid")

        if join_args.join_condition and join_args.join_condition.join_expression:
            return self.evaluate_expression(
                join_args.join_condition.join_expression.expression,
                {
                    "t1": _,
                    "t2": right_table,
                },
            )
        else:
            return left_eq_right_condition(
                join_args.left_column or join_args.join_condition.left_column,
                join_args.right_column or join_args.join_condition.right_column,
            )

    def apply_union(self, union_args):
        other_table = self.get_table_or_query(union_args.table)

        # Ensure both tables have the same columns
        # Add missing columns with None values
        for col, dtype in self.query.schema().items():
            if col not in other_table.columns:
                other_table = other_table.mutate(
                    **{
                        col: ibis.literal(None).cast(dtype).name(col),
                    }
                )

        for col, dtype in other_table.schema().items():
            if col not in self.query.columns:
                self.query = self.query.mutate(
                    **{
                        col: ibis.literal(None).cast(dtype).name(col),
                    }
                )

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

        left = getattr(_, filter_column.column_name)
        operator_fn = self.get_operator(filter_operator)

        if operator_fn is None:
            frappe.throw(f"Operator {filter_operator} is not supported")

        right_column = (
            getattr(_, filter_value.column_name)
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
        old_name = rename_args.column.column_name
        new_name = frappe.scrub(rename_args.new_name)
        return self.query.rename(**{new_name: old_name})

    def apply_remove(self, remove_args):
        return self.query.drop(*remove_args.column_names)

    def apply_cast(self, cast_args):
        col_name = cast_args.column.column_name
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
        new_name = frappe.scrub(mutate_args.new_name)
        dtype = self.get_ibis_dtype(mutate_args.data_type)
        new_column = self.evaluate_expression(mutate_args.expression.expression)
        new_column = new_column.cast(dtype)
        return self.query.mutate(**{new_name: new_column})

    def apply_summary(self, summarize_args):
        aggregates = {
            frappe.scrub(measure.measure_name): self.translate_measure(measure)
            for measure in summarize_args.measures
        }
        group_bys = [
            self.translate_dimension(dimension)
            for dimension in summarize_args.dimensions
        ]
        return self.query.aggregate(**aggregates, by=group_bys)

    def apply_order_by(self, order_by_args):
        order_fn = ibis.asc if order_by_args.direction == "asc" else ibis.desc
        return self.query.order_by(order_fn(order_by_args.column.column_name))

    def apply_limit(self, limit_args):
        return self.query.limit(limit_args.limit)

    def apply_pivot(self, pivot_args, pivot_type):
        rows = {
            dimension.column_name: self.translate_dimension(dimension)
            for dimension in pivot_args["rows"]
        }
        columns = {
            dimension.column_name: self.translate_dimension(dimension)
            for dimension in pivot_args["columns"]
        }
        values = {
            frappe.scrub(measure.measure_name): self.translate_measure(measure)
            for measure in pivot_args["values"]
        }

        if pivot_type == "wider":
            names = self.query.select(columns.keys()).distinct().limit(10).execute()
            return (
                self.query.group_by(*rows.values(), *columns.values())
                .aggregate(**values)
                .filter(
                    ibis.or_(
                        *[getattr(_, col).isin(names[col]) for col in columns.keys()]
                    )
                )
                .pivot_wider(
                    id_cols=rows.keys(),
                    names_from=columns.keys(),
                    names_sort=True,
                    values_from=values.keys(),
                    values_agg="sum",
                )
            )

        return self.query

    def apply_custom_operation(self, operation):
        return self.evaluate_expression(
            operation.expression.expression,
            additonal_context={
                "q": self.query,
            },
        )

    def translate_measure(self, measure):
        if measure.column_name == "count" and measure.aggregation == "count":
            return _.count()

        if "expression" in measure:
            column = self.evaluate_expression(measure.expression.expression)
            dtype = self.get_ibis_dtype(measure.data_type)
            measure_name = frappe.scrub(measure.measure_name)
            return column.cast(dtype).name(measure_name)

        column = getattr(_, measure.column_name)
        return self.apply_aggregate(column, measure.aggregation)

    def translate_dimension(self, dimension):
        col = getattr(_, dimension.column_name)
        if (
            dimension.data_type in ["Date", "Time", "Datetime"]
            and dimension.granularity
        ):
            col = self.apply_granularity(col, dimension.granularity)
            col = col.cast(self.get_ibis_dtype(dimension.data_type))
            col = col.name(dimension.column_name)
        return col

    def apply_aggregate(self, column, aggregate_function):
        return {
            "sum": column.sum(),
            "avg": column.mean(),
            "count": column.count(),
            "min": column.min(),
            "max": column.max(),
            "count_distinct": column.nunique(),
        }[aggregate_function]

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

        context = frappe._dict()
        context.q = _
        context.update(self.get_current_columns())
        context.update(get_functions())
        context.update(additonal_context or {})

        return exec_with_return(expression, context)

    def get_current_columns(self):
        # TODO: handle collisions with function names
        return {col: getattr(_, col) for col in self.query.schema().names}


def execute_ibis_query(
    query: IbisQuery, query_name=None, limit=100, cache=False, cache_expiry=3600
) -> pd.DataFrame:
    query = query.head(limit) if limit else query
    sql = ibis.to_sql(query)

    if cache and has_cached_results(sql):
        return get_cached_results(sql)

    start = time.monotonic()
    res: pd.DataFrame = query.execute()
    create_execution_log(sql, flt(time.monotonic() - start, 3), query_name)

    res = res.replace({pd.NaT: None, np.nan: None})

    if cache:
        # TODO: fix: pivot queries are not same, so cache key is always different
        cache_results(sql, res, cache_expiry)

    return res


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
    if dtype.is_boolean():
        return "Boolean"
    if dtype.is_uuid():
        return "UUID"
    frappe.throw(f"Cannot infer data type for: {dtype}")


def cache_results(sql, result: pd.DataFrame, cache_expiry=3600):
    cache_key = make_digest(sql)
    cache_key = "insights:query_results:" + cache_key
    data = result.to_dict(orient="records")
    data = frappe.as_json(data)
    frappe.cache().set_value(cache_key, data, expires_in_sec=cache_expiry)


def get_cached_results(sql) -> pd.DataFrame:
    cache_key = make_digest(sql)
    cache_key = "insights:query_results:" + cache_key
    data = frappe.cache().get_value(cache_key)
    if not data:
        return None
    data = frappe.parse_json(data)
    df = pd.DataFrame(data).replace({pd.NaT: None, np.nan: None})
    return df


def has_cached_results(sql):
    cache_key = make_digest(sql)
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
        safe_exec(ast.unparse(a), _globals, _locals)
        return safe_eval(last_expression, _globals, _locals)
    else:
        return safe_eval(code, _globals, _locals)
