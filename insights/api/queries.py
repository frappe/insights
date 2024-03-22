import frappe
import ibis
from ibis import _

from insights.api.telemetry import track
from insights.decorators import check_role
from insights.insights.doctype.insights_query.utils import (
    get_columns_with_inferred_types,
)
from insights.insights.doctype.insights_team.insights_team import (
    get_allowed_resources_for_user,
)
from insights.insights.query_builders.sql_functions import handle_timespan


@frappe.whitelist()
@check_role("Insights User")
def get_queries():
    allowed_queries = get_allowed_resources_for_user("Insights Query")
    if not allowed_queries:
        return []

    Query = frappe.qb.DocType("Insights Query")
    QueryChart = frappe.qb.DocType("Insights Chart")
    DataSource = frappe.qb.DocType("Insights Data Source")
    User = frappe.qb.DocType("User")
    return (
        frappe.qb.from_(Query)
        .left_join(QueryChart)
        .on(QueryChart.query == Query.name)
        .left_join(User)
        .on(Query.owner == User.name)
        .left_join(DataSource)
        .on(Query.data_source == DataSource.name)
        .select(
            Query.name,
            Query.title,
            Query.status,
            Query.is_assisted_query,
            Query.is_native_query,
            Query.is_stored,
            Query.data_source,
            Query.creation,
            Query.owner,
            User.full_name.as_("owner_name"),
            User.user_image.as_("owner_image"),
            QueryChart.chart_type,
            DataSource.title.as_("data_source_title"),
        )
        .where(Query.name.isin(allowed_queries))
        .groupby(Query.name)
        .orderby(Query.creation, order=frappe.qb.desc)
    ).run(as_dict=True)


@frappe.whitelist()
@check_role("Insights User")
def create_query(**query):
    track("create_query")
    doc = frappe.new_doc("Insights Query")
    doc.title = query.get("title")
    doc.data_source = query.get("data_source")
    doc.status = "Execution Successful"
    doc.is_assisted_query = query.get("is_assisted_query")
    doc.is_native_query = query.get("is_native_query")
    doc.is_script_query = query.get("is_script_query")
    if query.get("is_script_query"):
        doc.data_source = "Query Store"
    if table := query.get("table") and not doc.is_assisted_query:
        doc.append(
            "tables",
            {
                "table": table.get("value"),
                "label": table.get("label"),
            },
        )
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def create_chart():
    chart = frappe.new_doc("Insights Chart")
    chart.save()
    return chart.name


@frappe.whitelist()
def pivot(data, indexes: list[str] = None, columns: list[str] = None, values: list[str] = None):
    indexes = indexes or []
    columns = columns or []
    values = values or []
    if not data or not (indexes + columns + values):
        return []

    import pandas as pd

    df = pd.DataFrame(data)
    for value_column in values:
        try:
            df[value_column] = df[value_column].astype(float).fillna(0).round(2)
        except ValueError:
            # if the value is not a number, then convert it to 1
            # this will show the count of records
            df[value_column] = df[value_column].apply(lambda x: 1)

    pivot = pd.pivot_table(
        df, index=indexes, columns=columns, values=values, sort=False, fill_value=0, aggfunc="sum"
    )
    pivot = pivot.reset_index()
    pivot = pivot.to_dict("records")

    return flatten_column_keys(pivot)


def flatten_column_keys(pivoted_records: list[dict]):
    """
    - Move the values to the bottom level
    - Flatten the column names

    Input:
    df = [{ ("Date", "", ""): "2018-01-01", ("Region", "", ""): "A", ("Price", "OK", "No"): 100, ...}]

    Output:
    df = [{ "Date": "2018-01-01", "Region": "A", "OK___No__Price": 100, ...}]
    """
    new_records = []
    for row in pivoted_records:
        new_row = {}
        cols = list(row.keys())
        if type(cols[0]) != tuple:
            new_records.append(row)
            continue
        for keys in cols:
            first_key = keys[0]
            new_keys = list(keys[1:]) + [first_key]
            new_keys = [key for key in new_keys if key]
            new_key = "___".join(new_keys)
            new_row[new_key] = row[keys]
        new_records.append(new_row)
    return new_records


def deep_convert_dict_to_dict(d):
    if isinstance(d, dict):
        new_dict = frappe._dict()
        for k, v in d.items():
            new_dict[k] = deep_convert_dict_to_dict(v)
        return new_dict

    if isinstance(d, list):
        new_list = []
        for v in d:
            new_list.append(deep_convert_dict_to_dict(v))
        return new_list

    return d


_dict = deep_convert_dict_to_dict


@frappe.whitelist()
def execute_query_pipeline(data_source, query_pipeline):
    doc = frappe.get_doc("Insights Data Source", data_source)

    conn = doc.get_ibis_connection()
    translator = QueryPipelineTranslator(query_pipeline, backend=conn)
    query = translator.translate()
    sql = ibis.to_sql(query.head(100), dialect="mysql")

    data = doc.execute_query(sql, return_columns=True)
    data[0] = get_columns_with_inferred_types(data)
    return data


@frappe.whitelist()
def get_distinct_column_values(data_source, query_pipeline, column_name, search_term=None):
    doc = frappe.get_doc("Insights Data Source", data_source)

    conn = doc.get_ibis_connection()
    translator = QueryPipelineTranslator(query_pipeline, backend=conn)
    query = translator.translate()
    values_query = (
        query.select(column_name)
        .filter(
            getattr(_, column_name).notnull()
            if not search_term
            else getattr(_, column_name).like(f"%{search_term}%")
        )
        .distinct()
        .head(20)
    )
    sql = ibis.to_sql(values_query)
    values = doc.execute_query(sql, pluck=True)
    return values


@frappe.whitelist()
def get_min_max(data_source, query_pipeline, column_name):
    doc = frappe.get_doc("Insights Data Source", data_source)

    conn = doc.get_ibis_connection()
    translator = QueryPipelineTranslator(query_pipeline, backend=conn)
    query = translator.translate()
    values_query = query.select(column_name).aggregate(
        min=getattr(_, column_name).min(), max=getattr(_, column_name).max()
    )
    sql = ibis.to_sql(values_query)
    values = doc.execute_query(sql)
    return values[0]


class QueryPipelineTranslator:
    def __init__(self, pipeline_steps, backend=None):
        self.query = None
        self.db_backend = backend
        self.pipeline_steps = pipeline_steps

    def translate(self):
        self.query = None
        for step in self.pipeline_steps:
            handler = self.get_step_handler(step)
            self.query = handler(self.query)
        return self.query

    def get_table(self, table_name):
        # VUL: Any table can be accessed
        return self.db_backend.table(table_name)

    def get_step_handler(self, step):
        step = _dict(step)
        handler = lambda query: query
        if step.type == "source":
            handler = self.translate_source(step)
        elif step.type == "join":
            handler = self.translate_join(step)
        elif step.type == "filter":
            handler = self.translate_filter(step)
        elif step.type == "select":
            handler = self.translate_select(step)
        elif step.type == "rename":
            handler = self.translate_rename(step)
        elif step.type == "remove":
            handler = self.translate_remove(step)
        elif step.type == "mutate":
            handler = self.translate_mutate(step)
        elif step.type == "cast":
            handler = self.translate_cast(step)
        elif step.type == "summarize":
            handler = self.translate_summary(step)
        # elif step.type == "group_by":
        #     handler = self.translate_group_by(step)
        elif step.type == "order_by":
            handler = self.translate_order_by(step)
        elif step.type == "limit":
            handler = self.translate_limit(step)
        elif step.type == "pivot_wider":
            handler = self.translate_pivot(step, "wider")
        return handler

    def translate_source(self, source_args):
        table = self.get_table(source_args.table.table_name)
        return lambda _: table.select(table)

    def translate_join(self, join_args):
        right_table = self.get_table(join_args.table.table_name)
        left_column = getattr(_, join_args.left_column.column_name)
        right_column = getattr(right_table, join_args.right_column.column_name)
        join_on = left_column == right_column
        return lambda query: query.join(right_table, join_on)

    def translate_filter(self, filter_args):
        filter_column = filter_args.column
        filter_operator = filter_args.operator
        filter_value = filter_args.value

        left = getattr(_, filter_column.column_name)
        operator_fn = self.get_operator(filter_operator)

        right_column = (
            getattr(_, filter_value.column_name) if hasattr(filter_value, "column_name") else None
        )

        right_value = right_column or filter_value
        return lambda query: query.filter(operator_fn(left, right_value))

    def get_operator(self, operator):
        return {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            "=": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "between": lambda x, y: x.between(y[0], y[1]),
            "contains": lambda x, y: x.like(y),
            "not_contains": lambda x, y: ~x.like(y),
            "in": lambda x, y: x.isin(y),
            "not_in": lambda x, y: ~x.isin(y),
            "is_set": lambda x, y: x.notnull(),
            "is_not_set": lambda x, y: x.isnull(),
            "within": lambda x, y: handle_timespan(x, y),
        }[operator]

    def translate_select(self, select_args):
        select_args = _dict(select_args)
        if select_args.column_names:
            columns = [getattr(_, col.column_name) for col in select_args.column_names]
            return lambda query: query[columns]
        if select_args.expression:
            expression = self.translate_col_expression(select_args.expression)
            return lambda query: query.select(expression)
        raise ValueError("Select must have either column_names or expression")

    def translate_rename(self, rename_args):
        old_name = rename_args.column.column_name
        return lambda query: query.rename(**{rename_args.new_name: old_name})

    def translate_remove(self, remove_args):
        return lambda query: query.drop(*remove_args.column_names)

    def translate_cast(self, cast_args):
        col_name = cast_args.column.column_name
        dtype = {
            "String": "string",
            "Integer": "int64",
            "Decimal": "float64",
            "Date": "date",
            "Datetime": "timestamp",
            "Time": "time",
            "Text": "string",
        }[cast_args.data_type]
        return lambda query: query.cast({col_name: dtype})

    def translate_mutate(self, mutate_args):
        label = mutate_args.label
        new_column = self.translate_col_expression(mutate_args.mutation)
        return lambda query: query.mutate(**{label: new_column})

    def translate_summary(self, summarize_args):
        metrics_by_name = summarize_args.metrics
        group_bys = summarize_args.by
        aggregates = {
            label: self.translate_col_expression(metric)
            for label, metric in metrics_by_name.items()
        }
        group_bys = [self.translate_col_expression(by) for by in group_bys]
        return lambda query: query.aggregate(**aggregates, by=group_bys)

    # def translate_group_by(self, group_by_args):
    #     return self.translate_aggregate(group_by_args)

    def translate_order_by(self, order_by_args):
        column = self.translate_col_expression(order_by_args.column)
        column = column.asc() if order_by_args.direction == "asc" else column.desc()
        return lambda query: query.order_by(column)

    def translate_limit(self, limit_args):
        return lambda query: query.limit(limit_args.limit)

    def translate_pivot(self, pivot_args, pivot_type):
        # if not ibis.options.default_backend:
        #     raise ValueError("No backend set")

        # id_cols = self.translate_col_expression(pivot_args.id_cols)
        # names_from = self.translate_col_expression(pivot_args.names_from)
        # values_from = self.translate_col_expression(pivot_args.values_from)
        # values_agg = pivot_args.values_agg
        if pivot_type == "wider":
            return lambda query: query.pivot_wider(
                id_cols=pivot_args.id_cols.colum_name,
                names_from=pivot_args.names_from.column_name,
                values_from=pivot_args.values_from.column_name,
                values_agg=pivot_args.values_agg,
            )
        return lambda query: query

    def translate_col_expression(self, expr):
        expr = frappe._dict(expr)

        if expr.type == "column":
            column = getattr(_, expr.column_name)
            if not expr.options:
                return column
            if expr.options.granularity:
                column = self.apply_granularity(column, expr.options.granularity)
            if expr.options.date_format:
                column = column.strftime(expr.options.date_format)
            if expr.options.aggregate:
                column = self.apply_aggregate(column, expr.options.aggregate)
            return column

        if expr.type == "expression":
            return self.evaluate_expression(expr.expression)

        # if expr.type == "window_operation":
        #     return self.translate_window_operation(expr)

        raise ValueError(f"Unknown expression type {expr.type}")

    def apply_aggregate(self, column, aggregate_function):
        return {
            "sum": column.sum(),
            "avg": column.mean(),
            "count": column.count(),
        }[aggregate_function]

    def apply_granularity(self, column, granularity):
        return {
            "day": column.day(),
            "month": column.month(),
            "year": column.year(),
        }[granularity]

    def evaluate_expression(self, expression):
        context = frappe._dict(
            q=_,
            columns=ibis.selectors.c,
            case=ibis.case,
            row_number=ibis.row_number,
        )
        stripped_expression = expression.strip().replace("\n", "").replace("\t", "")
        return frappe.safe_eval(stripped_expression, context)
