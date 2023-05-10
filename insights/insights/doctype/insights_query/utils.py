# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import frappe
import pandas as pd
import sqlparse
from frappe import _dict

from insights.utils import ResultColumn


class InsightsChart:
    @classmethod
    def get_name(cls, *args, **kwargs):
        return frappe.db.exists("Insights Chart", kwargs)


class InsightsTable:
    @classmethod
    def get_name(cls, *args, **kwargs):
        return frappe.db.exists("Insights Table", kwargs)

    @classmethod
    def get_doc(cls, *args, **kwargs):
        kwargs = {"name": args[0]} if len(args) > 0 else kwargs
        return frappe.get_doc("Insights Table", kwargs)


class InsightsColumn:
    @classmethod
    def from_dict(cls, obj):
        column = _dict(
            label=obj.get("label") or obj.get("column"),
            column=obj.get("column") or obj.get("label"),
            type=obj.get("type") or "String",
        )
        if not column.label:
            frappe.throw("Column Label is required")
        if not column.column:
            frappe.throw("Column Name is required")
        return column

    @classmethod
    def from_dicts(cls, objs):
        return [InsightsColumn.from_dict(obj) for obj in objs]


class InsightsDataSource:
    @classmethod
    def get_doc(cls, name):
        return frappe.get_doc("Insights Data Source", name)


class InsightsSettings:
    @classmethod
    def get(cls, key):
        return frappe.db.get_single_value("Insights Settings", key)


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


def format_query(query):
    return sqlparse.format(
        str(query),
        keyword_case="upper",
        reindent_aligned=True,
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
    result_columns = [
        ResultColumn.from_args(c, value_column["type"]) for c in new_columns[1:]
    ]
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
        pd.to_numeric(value, downcast="float")
        return "Decimal"
    except ValueError:
        try:
            # test if integer
            pd.to_numeric(value)
            return "Integer"
        except ValueError:
            try:
                # test if datetime
                pd.to_datetime(value)
                return "Datetime"
            except ValueError:
                return "String"


def infer_type_from_list(values):
    inferred_types = [infer_type(v) for v in values]
    if "String" in inferred_types:
        return "String"
    if "Datetime" in inferred_types:
        return "Datetime"
    if "Decimal" in inferred_types:
        return "Decimal"
    if "Integer" in inferred_types:
        return "Integer"


# assisted query utils


class GetMixin:
    def get(self, key):
        # to make obj.get("key") work
        return self.__dict__.get(key)


class RequiredFieldsMixin:
    def __bool__(self):
        if not hasattr(self, "OPTIONAL_FIELDS"):
            return all(self.__dict__.values())

        # check if NON_OPTIONAL_FIELDS are not None
        NON_OPTIONAL_FIELDS = (
            f for f in self.__dict__.keys() if f not in self.OPTIONAL_FIELDS
        )
        return all(self.get(f) for f in NON_OPTIONAL_FIELDS)


@dataclass
class LabelValue(GetMixin, RequiredFieldsMixin):
    value: str = None
    label: Optional[str] = None
    OPTIONAL_FIELDS = ["label"]

    @staticmethod
    def from_dict(d):
        d = d or {}
        value, label = d.get("value"), d.get("label")
        return LabelValue(value, label or value)


@dataclass
class QueryTable(GetMixin, RequiredFieldsMixin):
    table: str = None
    label: Optional[str] = None
    OPTIONAL_FIELDS = ["label"]

    @staticmethod
    def from_dict(d):
        d = d or {}
        table, label = d.get("table"), d.get("label")
        return QueryTable(table, label or table)


@dataclass
class QueryColumn(GetMixin, RequiredFieldsMixin):
    table: str = None
    column: str = None
    type: str = None
    label: Optional[str] = None
    OPTIONAL_FIELDS = ["label"]

    @staticmethod
    def from_dict(d):
        d = d or {}
        table, column, label, type = (
            d.get("table"),
            d.get("column"),
            d.get("label"),
            d.get("type", "String"),
        )
        return QueryColumn(table, column, type, label or column)


@dataclass
class Join(GetMixin, RequiredFieldsMixin):
    left_table: QueryTable = QueryTable()
    right_table: QueryTable = QueryTable()
    join_type: LabelValue = LabelValue()
    left_column: QueryColumn = QueryColumn()
    right_column: QueryColumn = QueryColumn()

    @staticmethod
    def from_dict(d):
        d = d or {}
        left_table = QueryTable.from_dict(d.get("left_table"))
        right_table = QueryTable.from_dict(d.get("right_table"))
        left_column = QueryColumn.from_dict(d.get("left_column"))
        right_column = QueryColumn.from_dict(d.get("right_column"))
        join_type = LabelValue.from_dict(d.get("join_type"))
        return Join(left_table, right_table, join_type, left_column, right_column)


@dataclass
class Filter(GetMixin, RequiredFieldsMixin):
    column: QueryColumn = QueryColumn()
    operator: LabelValue = LabelValue()
    value: LabelValue = LabelValue()

    @staticmethod
    def from_dict(d):
        d = d or {}
        column = QueryColumn.from_dict(d.get("column"))
        operator = LabelValue.from_dict(d.get("operator"))
        value = LabelValue.from_dict(d.get("value"))
        return Filter(column, operator, value)


@dataclass
class Metric(GetMixin, RequiredFieldsMixin):
    column: QueryColumn = QueryColumn()
    aggregation: LabelValue = LabelValue()
    alias: Optional[str] = None
    OPTIONAL_FIELDS = ["alias"]

    @staticmethod
    def from_dict(d):
        d = d or {}
        column = QueryColumn.from_dict(d.get("column"))
        aggregation = LabelValue.from_dict(d.get("aggregation"))
        alias = d.get("alias", column.label)
        return Metric(column, aggregation, alias)


@dataclass
class Dimension(GetMixin, RequiredFieldsMixin):
    column: QueryColumn = QueryColumn()
    alias: Optional[str] = None
    OPTIONAL_FIELDS = ["alias"]

    @staticmethod
    def from_dict(d):
        d = d or {}
        column = QueryColumn.from_dict(d.get("column"))
        alias = d.get("alias")
        return Dimension(column, alias or column.label)


@dataclass
class Summarise(GetMixin, RequiredFieldsMixin):
    metrics: list[Metric] = field(default_factory=list)
    dimensions: list[Dimension] = field(default_factory=list)

    @staticmethod
    def from_dict(d):
        d = d or {}
        metrics = [Metric.from_dict(m) for m in d.get("metrics", [])]
        dimensions = [Dimension.from_dict(m) for m in d.get("dimensions", [])]
        metrics = [m for m in metrics if m]
        dimensions = [d for d in dimensions if d]
        return Summarise(metrics, dimensions)


@dataclass
class Column(GetMixin, RequiredFieldsMixin):
    column: QueryColumn = QueryColumn()
    alias: Optional[str] = None
    OPTIONAL_FIELDS = ["alias"]

    @staticmethod
    def from_dict(d):
        d = d or {}
        column = QueryColumn.from_dict(d.get("column"))
        alias = d.get("alias")
        return Column(column, alias or column.label)


@dataclass
class OrderBy(GetMixin, RequiredFieldsMixin):
    column: QueryColumn = QueryColumn()
    order: LabelValue = LabelValue()
    DEFAULT_ORDER = "asc"

    @classmethod
    def from_dict(cls, d):
        d = d or {}
        column = QueryColumn.from_dict(d.get("column"))
        order = LabelValue(d.get("order", cls.DEFAULT_ORDER))
        return OrderBy(column, order)


@dataclass
class AssistedQuery(GetMixin, RequiredFieldsMixin):
    table: QueryTable = QueryTable()
    joins: list[Join] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    summarise: Summarise = Summarise()
    columns: list[Column] = field(default_factory=list)
    order_by: list[OrderBy] = field(default_factory=list)
    limit: int = None
    OPTIONAL_FIELDS = ["joins", "filters", "summarise", "columns", "order_by", "limit"]

    @staticmethod
    def from_dict(d):
        d = d or {}
        table = QueryTable.from_dict(d.get("table"))
        joins = [Join.from_dict(j) for j in d.get("joins")]
        filters = [Filter.from_dict(f) for f in d.get("filters")]
        summarise = Summarise.from_dict(d.get("summarise"))
        columns = [Column.from_dict(c) for c in d.get("columns")]
        order_by = [OrderBy.from_dict(o) for o in d.get("order_by")]
        limit = d.get("limit")

        joins = [j for j in joins if j]
        filters = [f for f in filters if f]
        columns = [c for c in columns if c]
        order_by = [o for o in order_by if o]

        return AssistedQuery(table, joins, filters, summarise, columns, order_by, limit)
