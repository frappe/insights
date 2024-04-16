# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from dataclasses import dataclass
from enum import Enum

import frappe
import pandas as pd
import sqlparse
from frappe import _dict

from insights.utils import InsightsDataSource, ResultColumn


class QueryStatus(Enum):
    PENDING = "Pending Execution"
    SUCCESS = "Execution Successful"
    FAILED = "Execution Failed"


def update_sql(query):
    query.status = QueryStatus.SUCCESS.value
    if not query.data_source:
        return
    data_source = InsightsDataSource.get_doc(query.data_source)
    sql = data_source.build_query(query)
    sql = format_query(sql)
    if query.sql == sql:
        return
    query.sql = sql
    query.update_query_results()
    query.status = QueryStatus.PENDING.value if sql else QueryStatus.SUCCESS.value


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
    if not (options.get("column") and options.get("index") and options.get("value")):
        return results

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
        fill_value=0,
        sort=False,
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


def apply_cumulative_sum(columns, results):
    if not columns:
        return results

    column_names = [d["label"] for d in results[0]]
    results_df = pd.DataFrame(results[1:], columns=column_names)

    for column in columns:
        results_df[column.get("label")] = (
            results_df[column.get("label")].astype(float).cumsum().fillna(0)
        )

    return [results[0]] + results_df.values.tolist()


def infer_type(value):
    try:
        # test if decimal
        val = pd.to_numeric(value)
        if val % 1 == 0:
            return "Integer"
        return "Decimal"
    except Exception:
        try:
            # test if datetime
            pd.to_datetime(value)
            return "Datetime"
        except Exception:
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
        return (
            self.aggregation
            and self.aggregation.lower() != "custom"
            and self.aggregation.lower() != "group by"
        )

    def is_expression(self):
        return (
            self.expression
            and self.expression.get("raw")
            and self.expression.get("ast")
            and self.alias
        )

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

    def is_measure(self):
        # TODO: if is_expression and is_aggregate then it is a measure (can't determine if aggregation is set)
        return (
            self.is_numeric_type()
            or self.is_aggregate()
            or (self.is_expression() and self.is_numeric_type())
        )

    def is_dimension(self):
        return not self.is_measure()


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


class JoinColumn(frappe._dict):
    def __init__(self, *args, **kwargs):
        self.table = kwargs.get("table")
        self.column = kwargs.get("column")
        self.value = kwargs.get("column")
        self.label = kwargs.get("label") or kwargs.get("column")

    def is_valid(self):
        return bool(self.table and self.column)


@dataclass
class Join(frappe._dict):
    def __init__(self, *args, **kwargs):
        self.left_table = Table(**kwargs.get("left_table"))
        self.right_table = Table(**kwargs.get("right_table"))
        self.join_type = LabelValue(**kwargs.get("join_type"))
        self.left_column = JoinColumn(**kwargs.get("left_column"))
        self.right_column = JoinColumn(**kwargs.get("right_column"))

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
        self.column = Column(**(kwargs.get("column") or {}))
        self.operator = LabelValue(**(kwargs.get("operator") or {}))
        self.value = LabelValue(**(kwargs.get("value") or {}))
        self.expression = frappe.parse_json(kwargs.get("expression", {}))

    def is_valid(self):
        if self.expression.get("raw") and self.expression.get("ast"):
            return True
        if self.operator.value in ["is_set", "is_not_set"]:
            return self.column.is_valid() and self.operator.is_valid()
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

    def add_filter(self, column, operator, value):
        if not isinstance(value, dict):
            value = {"value": value}
        if not isinstance(operator, dict):
            operator = {"value": operator}
        if not column or not isinstance(column, dict):
            frappe.throw("Invalid Column")

        is_filter_applied_to_column = any(
            f.column.column == column.get("column") and f.column.table == column.get("table")
            for f in self.filters
            if f.column.is_valid()
        )

        if not is_filter_applied_to_column:
            self.filters.append(Filter(column=column, value=value, operator=operator))
        else:
            # update existing filter
            for f in self.filters:
                if f.column.column == column.get("column") and f.column.table == column.get(
                    "table"
                ):
                    f.value = LabelValue(**value)
                    f.operator = LabelValue(**operator)
                    break

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


def export_query(doc):
    if not hasattr(doc.variant_controller, "export_query"):
        frappe.throw("The selected query type does not support exporting")

    exported_query = frappe._dict(
        data=doc.variant_controller.export_query(),
        metadata={
            "data_source": doc.data_source,
            "title": doc.title,
            "transforms": doc.transforms,
            "is_saved_as_table": doc.is_saved_as_table,
            "type": (
                "assisted"
                if doc.is_assisted_query
                else "native"
                if doc.is_native_query
                else "legacy"
            ),
        },
    )
    return exported_query


def import_query(data_source, query):
    query = frappe.parse_json(query)
    query.metadata = _dict(query.metadata)

    query_doc = frappe.new_doc("Insights Query")
    query_doc.data_source = data_source
    query_doc.title = query.metadata.title
    query_doc.is_assisted_query = query.metadata.type == "assisted"
    query_doc.is_native_query = query.metadata.type == "native"
    query_doc.is_legacy_query = query.metadata.type == "legacy"
    query_doc.set("transforms", query.metadata.transforms)
    query_doc.variant_controller.import_query(query.data)
    query_doc.save(ignore_permissions=True)

    if query.metadata.is_saved_as_table:
        query_doc.update_insights_table(force=True)
        frappe.enqueue_doc(
            "Insights Query",
            query_doc.name,
            "fetch_results",
            queue="long",
        )

    return query_doc.name


class BaseNestedQueryImporter:
    def __init__(self, data: dict, doc, imported_queries=None):
        self.doc = doc
        self.data = frappe._dict(data)
        self.imported_queries = imported_queries or {}

    def import_query(self):
        self._import_subqueries()
        self._update_subquery_references()
        self._update_doc()

    def _import_subqueries(self):
        if not self.data.subqueries:
            return
        for name, subquery in self.data.subqueries.items():
            if name in self.imported_queries:
                continue
            # FIX: imported_queries is not updated with the subqueries of the subquery
            new_name = import_query(self.doc.data_source, subquery)
            self.imported_queries[name] = new_name

    def _update_subquery_references(self):
        raise NotImplementedError

    def _update_doc(self):
        raise NotImplementedError
