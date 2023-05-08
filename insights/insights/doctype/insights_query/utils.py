# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from dataclasses import dataclass
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

    column_names = [d["label"] for d in results[0]]
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

    column_names = [d["label"] for d in results[0]]
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

    column_names = [d["label"] for d in results[0]]
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
        return self.__dict__.get(key)


@dataclass
class LabelValue(GetMixin):
    label: str
    value: str

    @staticmethod
    def from_dict(d):
        return LabelValue(d["label"], d["value"])


@dataclass
class QueryTable(GetMixin):
    table: str
    label: str
    data_source: Optional[str]

    @staticmethod
    def from_dict(d):
        return QueryTable(
            d["table"],
            d["label"],
            d.get("data_source"),
        )


@dataclass
class QueryColumn(GetMixin):
    table: str
    column: str
    label: str
    type: str

    @staticmethod
    def from_dict(d):
        return QueryColumn(d["table"], d["column"], d["label"], d["type"])


@dataclass
class Join(GetMixin):
    left_table: QueryTable
    right_table: QueryTable
    join_type: LabelValue
    left_column: QueryColumn
    right_column: QueryColumn

    @staticmethod
    def from_dict(d):
        return Join(
            QueryTable.from_dict(d["left_table"]),
            QueryTable.from_dict(d["right_table"]),
            LabelValue.from_dict(d["join_type"]),
            QueryColumn.from_dict(d["left_column"]),
            QueryColumn.from_dict(d["right_column"]),
        )


@dataclass
class Filter(GetMixin):
    column: QueryColumn
    operator: LabelValue
    value: LabelValue

    @staticmethod
    def from_dict(d):
        return Filter(
            QueryColumn.from_dict(d["column"]),
            LabelValue.from_dict(d["operator"]),
            LabelValue.from_dict(d["value"]),
        )


@dataclass
class Metric(GetMixin):
    column: QueryColumn
    aggregation: LabelValue
    label: Optional[str]

    @staticmethod
    def from_dict(d):
        return Metric(
            QueryColumn.from_dict(d["column"]),
            LabelValue.from_dict(d["aggregation"]),
            d.get("label", d["column"]["label"]),
        )


@dataclass
class Dimension(GetMixin):
    column: QueryColumn
    label: Optional[str]

    @staticmethod
    def from_dict(d):
        return Dimension(
            QueryColumn.from_dict(d["column"]),
            d.get("label", d["column"]["label"]),
        )


@dataclass
class Summarise(GetMixin):
    metrics: list[Metric]
    dimensions: list[Dimension]

    @staticmethod
    def from_dict(d):
        return Summarise(
            [Metric.from_dict(m) for m in d["metrics"]],
            [Dimension.from_dict(m) for m in d["dimensions"]],
        )


@dataclass
class Column(GetMixin):
    column: QueryColumn
    label: Optional[str]

    @staticmethod
    def from_dict(d):
        return Column(
            QueryColumn.from_dict(d["column"]),
            d.get("label", d["column"]["label"]),
        )


@dataclass
class OrderBy(GetMixin):
    column: QueryColumn
    order: LabelValue

    @staticmethod
    def from_dict(d):
        return OrderBy(
            QueryColumn.from_dict(d["column"]), LabelValue.from_dict(d["order"])
        )


@dataclass
class AssistedQuery(GetMixin):
    table: QueryTable
    joins: list[Join]
    filters: list[Filter]
    summarise: Summarise
    columns: list[Column]
    order_by: list[OrderBy]
    limit: int

    @staticmethod
    def from_dict(d):
        table = d.get("table")
        joins = d.get("joins")
        filters = d.get("filters")
        summarise = d.get("summarise")
        columns = d.get("columns")
        order_by = d.get("order_by")
        limit = d.get("limit")

        table = QueryTable.from_dict(table) if table else None
        joins = [Join.from_dict(j) for j in joins] if joins else []
        filters = [Filter.from_dict(f) for f in filters] if filters else []
        summarise = Summarise.from_dict(summarise) if summarise else None
        columns = [Column.from_dict(c) for c in columns] if columns else []
        orderby = [OrderBy.from_dict(o) for o in order_by] if order_by else []
        limit = int(limit) if limit else None

        return AssistedQuery(table, joins, filters, summarise, columns, orderby, limit)
