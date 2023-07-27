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
        super().__init__(*args, **kwargs)
        self.table = self.get("table")
        self.column = self.get("column")
        self.type = self.get("type") or "String"
        self.order = self.get("order")
        self.aggregation = self.get("aggregation")
        self.expression = frappe.parse_json(self.get("expression", {}))
        self.label = self.get("label") or self.get("alias") or self.get("column")
        self.alias = self.get("alias") or self.get("label") or self.get("column")
        self.format = self.get("format")
        self.meta = self.get("meta")
        self.granularity = self.get("granularity")

    def __repr__(self) -> str:
        return f"""Column(table={self.table}, column={self.column}, type={self.type}, label={self.label}, alias={self.alias}, aggregation={self.aggregation}, expression={self.is_expression()})"""

    def __bool__(self):
        return bool(self.table and self.column) or bool(self.is_expression())

    @staticmethod
    def from_dicts(dicts):
        columns = (Column(**d) for d in dicts)
        return [c for c in columns if c]

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
        super().__init__(*args, **kwargs)
        self.value = self.get("value")
        self.label = self.get("label") or self.get("value")

    def __bool__(self):
        return bool(self.value)


@dataclass
class Table(frappe._dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table = self.get("table")
        self.label = self.get("label") or self.get("table")

    def __bool__(self):
        return bool(self.table)


@dataclass
class Join(frappe._dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.left_table = Table(**self.get("left_table"))
        self.right_table = Table(**self.get("right_table"))
        self.join_type = LabelValue(**self.get("join_type"))
        self.left_column = Column(**self.get("left_column"))
        self.right_column = Column(**self.get("right_column"))

    def __bool__(self):
        return bool(
            self.left_table and self.right_table and self.left_column and self.right_column
        )

    @staticmethod
    def from_dicts(dicts):
        joins = [Join(**d) for d in dicts]
        return [j for j in joins if j]


@dataclass
class Filter(frappe._dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.column = Column(**self.get("column"))
        self.operator = LabelValue(**self.get("operator"))
        self.value = LabelValue(**self.get("value"))

    def __bool__(self):
        return bool(self.column and self.operator and self.value)

    @classmethod
    def from_dicts(cls, dicts):
        filters = [cls(**d) for d in dicts]
        return [f for f in filters if f]


@dataclass
class Query(frappe._dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table = Table(**kwargs.get("table"))
        self.joins = Join.from_dicts(kwargs.get("joins"))
        self.filters = Filter.from_dicts(kwargs.get("filters"))
        self.columns = Column.from_dicts(kwargs.get("columns"))
        self.calculations = Column.from_dicts(kwargs.get("calculations"))
        self.measures = Column.from_dicts(kwargs.get("measures"))
        self.dimensions = Column.from_dicts(kwargs.get("dimensions"))
        self.orders = Column.from_dicts(kwargs.get("orders"))
        self.limit = kwargs.get("limit")

    def __bool__(self):
        return bool(self.table)

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
