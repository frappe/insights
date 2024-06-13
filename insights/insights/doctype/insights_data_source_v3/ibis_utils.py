import time
from io import StringIO

import frappe
import ibis
import numpy as np
import pandas as pd
from frappe.utils.data import flt
from ibis import _
from ibis import selectors as s
from ibis.expr.datatypes import DataType
from ibis.expr.types import Table as IbisQuery

from insights.cache_utils import make_digest
from insights.utils import create_execution_log
from insights.utils import deep_convert_dict_to_dict as _dict

from .data_warehouse import DataWarehouse


class IbisQueryBuilder:
    def build(self, operations: list) -> IbisQuery:
        self.query = None
        for operation in operations:
            handler = self.get_operation_handler(operation)
            self.query = handler(self.query)
        return self.query

    def get_table(self, table):
        return DataWarehouse().get_table(
            table.data_source,
            table.table_name,
            sync=True,
        )

    def get_operation_handler(self, operation):
        operation = _dict(operation)
        handler = lambda query: query
        if operation.type == "source":
            handler = self.translate_source(operation)
        elif operation.type == "join":
            handler = self.translate_join(operation)
        elif operation.type == "filter":
            handler = self.translate_filter(operation)
        elif operation.type == "filter_group":
            handler = self.translate_filter_group(operation)
        elif operation.type == "select":
            handler = self.translate_select(operation)
        elif operation.type == "rename":
            handler = self.translate_rename(operation)
        elif operation.type == "remove":
            handler = self.translate_remove(operation)
        elif operation.type == "mutate":
            handler = self.translate_mutate(operation)
        elif operation.type == "cast":
            handler = self.translate_cast(operation)
        elif operation.type == "summarize":
            handler = self.translate_summary(operation)
        elif operation.type == "order_by":
            handler = self.translate_order_by(operation)
        elif operation.type == "limit":
            handler = self.translate_limit(operation)
        elif operation.type == "pivot_wider":
            handler = self.translate_pivot(operation, "wider")
        return handler

    def translate_source(self, source_args):
        table = self.get_table(source_args.table)
        return lambda _: table

    def translate_join(self, join_args):
        right_table = self.get_table(join_args.table)
        left_column = getattr(_, join_args.left_column.column_name)
        right_column = getattr(right_table, join_args.right_column.column_name)
        join_on = left_column == right_column
        join_type = join_args.join_type
        join_type = "outer" if join_type == "full" else join_type
        return lambda query: query.join(right_table, join_on, how=join_type).select(
            ~s.endswith("right")
        )

    def translate_filter(self, filter_args):
        condition = self.make_filter_condition(filter_args)
        return lambda query: query.filter(condition)

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
            "is_set": lambda x, y: x.notnull(),
            "is_not_set": lambda x, y: x.isnull(),
            "contains": lambda x, y: x.like(y),
            "not_contains": lambda x, y: ~x.like(y),
            "starts_with": lambda x, y: x.like(f"{y}%"),
            "ends_with": lambda x, y: x.like(f"%{y}"),
            "between": lambda x, y: x.between(y[0], y[1]),
            # "within": lambda x, y: handle_timespan(x, y),
        }[operator]

    def translate_filter_group(self, filter_group_args):
        filters = filter_group_args.filters
        logical_operator = filter_group_args.logical_operator
        conditions = [self.make_filter_condition(filter) for filter in filters]

        if logical_operator == "And":
            return lambda query: query.filter(ibis.and_(*conditions))
        elif logical_operator == "Or":
            return lambda query: query.filter(ibis.or_(*conditions))

        frappe.throw(f"Logical operator {logical_operator} is not supported")

    def translate_select(self, select_args):
        select_args = _dict(select_args)
        return lambda query: query.select(select_args.column_names)

    def translate_rename(self, rename_args):
        old_name = rename_args.column.column_name
        return lambda query: query.rename(**{rename_args.new_name: old_name})

    def translate_remove(self, remove_args):
        return lambda query: query.drop(*remove_args.column_names)

    def translate_cast(self, cast_args):
        col_name = cast_args.column.column_name
        dtype = self.get_ibis_dtype(cast_args.data_type)
        return lambda query: query.cast({col_name: dtype})

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

    def translate_mutate(self, mutate_args):
        new_name = mutate_args.new_name
        dtype = self.get_ibis_dtype(mutate_args.data_type)
        new_column = self.evaluate_expression(mutate_args.mutation.expression).cast(
            dtype
        )
        return lambda query: query.mutate(**{new_name: new_column})

    def translate_summary(self, summarize_args):
        measures = summarize_args.measures
        dimensions = summarize_args.dimensions
        aggregates = {
            measure.column_name: self.translate_measure(measure) for measure in measures
        }
        group_bys = [self.translate_dimension(dimension) for dimension in dimensions]
        return lambda query: query.aggregate(**aggregates, by=group_bys)

    def translate_order_by(self, order_by_args):
        order_fn = ibis.asc if order_by_args.direction == "asc" else ibis.desc
        return lambda query: query.order_by(order_fn(order_by_args.column.column_name))

    def translate_limit(self, limit_args):
        return lambda query: query.limit(limit_args.limit)

    def translate_pivot(self, pivot_args, pivot_type):
        rows = {
            dimension.column_name: self.translate_dimension(dimension)
            for dimension in pivot_args["rows"]
        }
        columns = {
            dimension.column_name: self.translate_dimension(dimension)
            for dimension in pivot_args["columns"]
        }
        values = {
            measure.column_name: self.translate_measure(measure)
            for measure in pivot_args["values"]
        }

        def _pivot_wider(query):
            return (
                query.group_by(*rows.values(), *columns.values())
                .aggregate(**values)
                .pivot_wider(
                    id_cols=rows.keys(),
                    names_from=columns.keys(),
                    values_from=values.keys(),
                    values_agg="sum",
                )
            )

        if pivot_type == "wider":
            return _pivot_wider

        return lambda query: query

    def translate_measure(self, measure):
        if measure.column_name == "count" and measure.aggregation == "count":
            return _.count()

        column = getattr(_, measure.column_name)
        return self.apply_aggregate(column, measure.aggregation)

    def translate_dimension(self, dimension):
        col = getattr(_, dimension.column_name)
        if dimension.granularity:
            col = self.apply_granularity(col, dimension.granularity)
            col = col.cast(self.get_ibis_dtype(dimension.data_type))
            col = col.name(dimension.column_name)
        return col

    def apply_aggregate(self, column, aggregate_function):
        return {
            "sum": column.sum(),
            "avg": column.mean(),
            "count": column.count(),
        }[aggregate_function]

    def apply_granularity(self, column, granularity):
        format_str = {
            "day": "%Y-%m-%d",
            "month": "%Y-%m-01",
            "year": "%Y-01-01",
        }
        if not format_str.get(granularity):
            frappe.throw(f"Granularity {granularity} is not supported")
        return column.strftime(format_str[granularity]).name(column.get_name())

    def evaluate_expression(self, expression):
        context = frappe._dict(
            q=_,
            columns=ibis.selectors.c,
            case=ibis.case,
            row_number=ibis.row_number,
            literal=ibis.literal,
        )
        stripped_expression = expression.strip().replace("\n", "").replace("\t", "")
        return frappe.safe_eval(stripped_expression, context)


def execute_ibis_query(
    query: IbisQuery, query_name=None, limit=100, cache=True
) -> pd.DataFrame:
    query = query.head(limit) if limit else query
    sql = ibis.to_sql(query)

    backend = query._find_backend(use_default=True)
    try:
        # make sure the connection is open
        backend.connect()
    except Exception as e:
        frappe.throw(f"Error connecting to the database: {e}")

    start = time.monotonic()
    res = backend.execute(query)
    create_execution_log(sql, flt(time.monotonic() - start, 3), query_name)

    res = res.replace({pd.NaT: None, np.NaN: 0})
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
    frappe.throw(f"Cannot infer data type for: {dtype}")


def cache_results(sql, result: pd.DataFrame):
    cache_key = make_digest(sql)
    cache_key = "insights:query_results:" + cache_key
    frappe.cache().set_value(cache_key, result.to_json(), expires_in_sec=3600)


def get_cached_results(sql) -> pd.DataFrame:
    cache_key = make_digest(sql)
    cache_key = "insights:query_results:" + cache_key
    res = frappe.cache().get_value(cache_key)
    return pd.read_json(StringIO(res)) if res else None


def has_cached_results(sql):
    cache_key = make_digest(sql)
    cache_key = "insights:query_results:" + cache_key
    return frappe.cache().get_value(cache_key) is not None
