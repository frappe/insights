# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from dataclasses import dataclass, field
from enum import Enum

import frappe
import pandas as pd
import sqlparse
from frappe import _dict

from insights.utils import InsightsDataSource, InsightsQuery, ResultColumn


class InsightsTableColumn:
    @classmethod
    def from_dict(cls, obj):
        column = _dict(
            label=obj.get("alias") or obj.get("label") or obj.get("column"),
            column=obj.get("alias") or obj.get("label") or obj.get("column"),
            type=obj.get("type") or "String",
        )
        if not column.label:
            frappe.throw("Column Label is required")
        if not column.column:
            frappe.throw("Column Name is required")
        return column

    @classmethod
    def from_dicts(cls, objs):
        return [InsightsTableColumn.from_dict(obj) for obj in objs]


class CachedResults:
    @classmethod
    def get(cls, query):
        key = f"insights_query_results:{query}"
        results_str = frappe.cache().get_value(key)
        if not results_str:
            return []
        results = frappe.parse_json(results_str)
        if not results:
            return []
        return results

    @classmethod
    def set(cls, query, results):
        key = f"insights_query_results:{query}"
        results_str = frappe.as_json(results)
        frappe.cache().set_value(key, results_str)


class Status(Enum):
    PENDING = "Pending Execution"
    SUCCESS = "Execution Successful"
    FAILED = "Pending Execution"


def update_sql(query):
    data_source = InsightsDataSource.get_doc(query.data_source)
    sql = data_source.build_query(query)
    sql = format_query(sql)
    if query.sql == sql:
        return
    query.sql = sql
    query.status = Status.PENDING.value


def format_query(query):
    return (
        sqlparse.format(
            str(query),
            keyword_case="upper",
            reindent_aligned=True,
            strip_comments=True,  # see: process_cte in sources/utils.py
        )
        if query
        else ""
    )


def apply_pivot_transform(results, options):
    options = frappe.parse_json(options)
    pivot_column = [c for c in results[0] if c["label"] == options.get("column")]
    index_column = [c for c in results[0] if c["label"] == options.get("index")]
    value_column = [c for c in results[0] if c["label"] == options.get("value")]

    if not (pivot_column and index_column and value_column):
        frappe.throw("Invalid Pivot Options")

    pivot_column = pivot_column[0]
    index_column = index_column[0]
    value_column = value_column[0]
    if pivot_column["label"] == index_column["label"]:
        frappe.throw("Pivot and Index columns cannot be the same")

    column_names = [d.get("label") for d in results[0]]
    results_df = pd.DataFrame(results[1:], columns=column_names)
    pivot_column_values = results_df[pivot_column["label"]]
    index_column_values = results_df[index_column["label"]]
    value_column_values = results_df[value_column["label"]]

    pivot_df = pd.DataFrame(
        {
            index_column["label"]: index_column_values,
            pivot_column["label"]: pivot_column_values,
            value_column["label"]: value_column_values,
        }
    )

    pivoted = pivot_df.pivot_table(
        index=index_column["label"],
        columns=pivot_column["label"],
        values=value_column["label"],
        aggfunc="sum",
    )

    pivoted = pivoted.reset_index()
    pivoted = pivoted.fillna(0)

    new_columns = pivoted.columns.to_list()
    result_index_column = ResultColumn.from_dict(index_column)
    result_columns = [ResultColumn.from_args(c, value_column["type"]) for c in new_columns[1:]]
    new_columns = [result_index_column] + result_columns
    return [new_columns] + pivoted.values.tolist()


def apply_unpivot_transform(results, options):
    options = frappe.parse_json(options)
    index_column = [c for c in results[0] if c["label"] == options.get("index_column")]
    new_column_label = options.get("column_label")
    value_label = options.get("value_label")

    if not (index_column and new_column_label and value_label):
        frappe.throw("Invalid Unpivot Options")

    column_names = [d.get("label") for d in results[0]]
    results_df = pd.DataFrame(results[1:], columns=column_names)

    index_column = index_column[0]
    results_columns = [
        ResultColumn.from_dict(index_column),
        ResultColumn.from_args(new_column_label, "String"),
        ResultColumn.from_args(value_label, "Decimal"),
    ]
    unpivoted = results_df.melt(
        id_vars=index_column["label"],
        var_name=new_column_label,
        value_name=value_label,
    )
    results_data = unpivoted.values.tolist()
    return [results_columns] + results_data


def apply_transpose_transform(results, options):
    options = frappe.parse_json(options)
    index_column = [c for c in results[0] if c["label"] == options.get("index_column")]
    new_column_label = options.get("column_label")

    if not (index_column and new_column_label):
        frappe.throw("Invalid Transpose Options")

    column_names = [d.get("label") for d in results[0]]
    results_df = pd.DataFrame(results[1:], columns=column_names)
    index_column = index_column[0]
    results_df = results_df.set_index(index_column["label"])
    results_df_transposed = results_df.transpose()
    results_df_transposed = results_df_transposed.reset_index()
    results_df_transposed.columns.name = None

    new_columns = results_df_transposed.columns.to_list()
    results_columns = [
        ResultColumn.from_args(new_column_label, "String"),
        *[
            ResultColumn.from_args(c, infer_type_from_list(results_df_transposed[c]))
            for c in new_columns[1:]
        ],
    ]
    results_data = results_df_transposed.values.tolist()
    return [results_columns] + results_data


def infer_type(value):
    try:
        # test if decimal
        val = pd.to_numeric(value)
        if val % 1 == 0:
            return "Integer"
        return "Decimal"
    except BaseException:
        try:
            # test if datetime
            pd.to_datetime(value)
            return "Datetime"
        except BaseException:
            return "String"


def infer_type_from_list(values):
    inferred_types = [infer_type(v) for v in values]
    if "String" in inferred_types:
        return "String"
    elif "Decimal" in inferred_types:
        return "Decimal"
    elif "Integer" in inferred_types:
        return "Integer"
    elif "Datetime" in inferred_types:
        return "Datetime"
    else:
        return "String"


def get_columns_with_inferred_types(results):
    columns = ResultColumn.from_dicts(results[0])
    column_names = [column.label for column in columns]
    results_df = pd.DataFrame(results[1:], columns=column_names)
    column_types = (infer_type_from_list(results_df[column_name]) for column_name in column_names)
    for column, column_type in zip(columns, column_types):
        column.type = column_type
    return columns


# assisted query utils


@dataclass
class Column(frappe._dict):
    def __init__(self, *args, **kwargs):
        self.table = kwargs.get("table")
        self.column = kwargs.get("column")
        self.type = kwargs.get("type") or "String"
        self.order = kwargs.get("order")
        self.aggregation = kwargs.get("aggregation")
        self.expression = frappe.parse_json(kwargs.get("expression", {}))
        self.label = kwargs.get("label") or kwargs.get("alias") or kwargs.get("column")
        self.alias = kwargs.get("alias") or kwargs.get("label") or kwargs.get("column")
        self.format = kwargs.get("format")
        self.meta = kwargs.get("meta")
        self.granularity = kwargs.get("granularity")

    def __repr__(self) -> str:
        return f"""Column(table={self.table}, column={self.column}, type={self.type}, label={self.label}, alias={self.alias}, aggregation={self.aggregation}, expression={self.is_expression()})"""

    def is_valid(self):
        return bool(self.table and self.column) or bool(self.is_expression())

    @staticmethod
    def from_dicts(dicts):
        return [Column(**d) for d in dicts]

    def is_aggregate(self):
        return self.aggregation and self.aggregation != "custom"

    def is_expression(self):
        return self.expression.get("raw") and self.expression.get("ast") and self.alias

    def is_formatted(self):
        return self.format

    def has_granularity(self):
        return self.is_date_type() and self.granularity

    def is_date_type(self):
        return self.type in ["Date", "Datetime"]

    def is_numeric_type(self):
        return self.type in ["Integer", "Decimal"]

    def is_string_type(self):
        return self.type in ["String", "Text"]


@dataclass
class LabelValue(frappe._dict):
    def __init__(self, *args, **kwargs):
        self.value = kwargs.get("value")
        self.label = kwargs.get("label") or kwargs.get("value")

    def is_valid(self):
        return bool(self.value)


@dataclass
class Table(frappe._dict):
    def __init__(self, *args, **kwargs):
        self.table = kwargs.get("table")
        self.label = kwargs.get("label") or kwargs.get("table")

    def is_valid(self):
        return bool(self.table)


@dataclass
class Join(frappe._dict):
    def __init__(self, *args, **kwargs):
        self.left_table = Table(**kwargs.get("left_table"))
        self.right_table = Table(**kwargs.get("right_table"))
        self.join_type = LabelValue(**kwargs.get("join_type"))
        self.left_column = Column(**kwargs.get("left_column"))
        self.right_column = Column(**kwargs.get("right_column"))

    def is_valid(self):
        return (
            self.left_table.is_valid()
            and self.right_table.is_valid()
            and self.left_column.is_valid()
            and self.right_column.is_valid()
        )

    @staticmethod
    def from_dicts(dicts):
        joins = [Join(**d) for d in dicts]
        return [j for j in joins if j]


@dataclass
class Filter(frappe._dict):
    def __init__(self, *args, **kwargs):
        self.column = Column(**kwargs.get("column"))
        self.operator = LabelValue(**kwargs.get("operator"))
        self.value = LabelValue(**kwargs.get("value"))

    def is_valid(self):
        return self.column.is_valid() and self.operator.is_valid() and self.value.is_valid()

    @classmethod
    def from_dicts(cls, dicts):
        filters = [cls(**d) for d in dicts]
        return [f for f in filters if f]


@dataclass
class Query(frappe._dict):
    def __init__(self, *args, **kwargs):
        self.table = Table(**kwargs.get("table"))
        self.joins = Join.from_dicts(kwargs.get("joins"))
        self.filters = Filter.from_dicts(kwargs.get("filters"))
        self.columns = Column.from_dicts(kwargs.get("columns"))
        self.calculations = Column.from_dicts(kwargs.get("calculations"))
        self.measures = Column.from_dicts(kwargs.get("measures"))
        self.dimensions = Column.from_dicts(kwargs.get("dimensions"))
        self.orders = Column.from_dicts(kwargs.get("orders"))
        self.limit = kwargs.get("limit")

    # not using __bool__ here because of a weird behavior
    # where when __bool__ returns False, and column is empty,
    # json.dumps will return empty dict instead of a dict with empty values
    def is_valid(self):
        return self.table.is_valid()

    def get_tables(self):
        tables = set()
        tables.add(self.table.table) if self.table else None
        for j in self.joins:
            tables.add(j.left_table.table) if j.left_table else None
            tables.add(j.right_table.table) if j.right_table else None
        return list(tables)

    def get_columns(self):
        return self._extract_columns()

    def _extract_columns(self):
        """
        Extract columns from columns, measures, dimensions
        A column has the following format: { table, column, type, label, alias, format }
        """
        columns = []
        for c in self.columns:
            columns.append(Column(**c))
        for c in self.measures:
            columns.append(Column(**c))
        for c in self.dimensions:
            columns.append(Column(**c))

        return [c for c in columns if c]


@dataclass
class ExportedQuery(frappe._dict):
    version: str
    query: Query
    subqueries: dict
    metadata: dict = field(default_factory=dict)

    def serialize(self):
        return frappe.as_json(self)

    @classmethod
    def deserialize(cls, data_str):
        data: ExportedQuery = frappe.parse_json(data_str)
        subqueries = {}
        for name, subquery in data.subqueries.items():
            subqueries[name] = cls.deserialize(subquery)
        return cls(
            version=data.version,
            query=Query(**data.query),
            subqueries=subqueries,
            metadata=data.metadata or {},
        )


class QueryExporter:
    def __init__(self, query: Query, metadata=None):
        self.query = query
        self._subqueries = {}
        self.metadata = metadata

    def export(self) -> ExportedQuery:
        self._subqueries = self._get_subqueries()
        return ExportedQuery(
            version="1.0",
            query=self.query,
            subqueries=self._subqueries,
            metadata=self.metadata,
        )

    def _get_subqueries(self):
        subqueries = frappe.get_all(
            "Insights Table",
            filters={
                "table": ["in", self.query.get_tables()],
                "is_query_based": 1,
            },
            pluck="table",
        )
        dependencies = {}
        for subquery in subqueries:
            if subquery in dependencies:
                continue
            query = InsightsQuery.get_doc(subquery)
            dependencies[query.name] = query.export_query()
        return dependencies


class QueryImporter:
    def __init__(self, data_source: str, exported_query: str, imported_subqueries=None):
        self.data_source = data_source
        self.exported_query = ExportedQuery.deserialize(exported_query)
        self._imported_subqueries = imported_subqueries or {}

    def import_query(self):
        self._import_subqueries()
        return self._import_query()

    def _import_subqueries(self):
        for name, subquery in self.exported_query.subqueries.items():
            query_importer = QueryImporter(self.data_source, subquery, self._imported_subqueries)
            new_name = query_importer.import_query()
            self._imported_subqueries[name] = new_name
        self._update_subquery_references()

    def _import_query(self):
        query = InsightsQuery.new_doc()
        query.data_source = self.data_source
        query.json = frappe.as_json(self.exported_query.query)
        for key, value in self.exported_query.metadata.items():
            query.set(key, value)
        query.save()
        if self.exported_query.metadata.get("is_saved_as_table"):
            query.update_insights_table(force=True)
            frappe.enqueue_doc(
                "Insights Query",
                query.name,
                "fetch_results",
                timeout=600,
                enqueue_after_commit=True,
            )
        return query.name

    def _update_subquery_references(self):
        for old_name, new_name in self._imported_subqueries.items():
            self._rename_subquery_in_table(old_name, new_name)
            self._rename_subquery_in_joins(old_name, new_name)
            self._rename_subquery_in_columns(old_name, new_name)
            self._rename_subquery_in_filters(old_name, new_name)
            self._rename_subquery_in_calculations(old_name, new_name)
            self._rename_subquery_in_measures(old_name, new_name)
            self._rename_subquery_in_dimensions(old_name, new_name)
            self._rename_subquery_in_orders(old_name, new_name)

    def _rename_subquery_in_table(self, old_name, new_name):
        if self.exported_query.query.table.table == old_name:
            self.exported_query.query.table.table = new_name

    def _rename_subquery_in_joins(self, old_name, new_name):
        for join in self.exported_query.query.joins:
            if join.left_table.table == old_name:
                join.left_table.table = new_name
            if join.right_table.table == old_name:
                join.right_table.table = new_name
            if join.left_column.table == old_name:
                join.left_column.table = new_name
            if join.right_column.table == old_name:
                join.right_column.table = new_name

    def _rename_subquery_in_columns(self, old_name, new_name):
        for column in self.exported_query.query.columns:
            if column.table == old_name:
                column.table = new_name

    def _rename_subquery_in_filters(self, old_name, new_name):
        for filter in self.exported_query.query.filters:
            if filter.column.table == old_name:
                filter.column.table = new_name

    def _rename_subquery_in_calculations(self, old_name, new_name):
        for calculation in self.exported_query.query.calculations:
            if calculation.table == old_name:
                calculation.table = new_name

    def _rename_subquery_in_measures(self, old_name, new_name):
        for measure in self.exported_query.query.measures:
            if measure.table == old_name:
                measure.table = new_name

    def _rename_subquery_in_dimensions(self, old_name, new_name):
        for dimension in self.exported_query.query.dimensions:
            if dimension.table == old_name:
                dimension.table = new_name

    def _rename_subquery_in_orders(self, old_name, new_name):
        for order in self.exported_query.query.orders:
            if order.table == old_name:
                order.table = new_name
