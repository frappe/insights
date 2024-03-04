import frappe
import ibis
from ibis import _

from insights.api.telemetry import track
from insights.decorators import check_role
from insights.insights.doctype.insights_team.insights_team import (
    get_allowed_resources_for_user,
)


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
def execute_query_pipeline(query_pipeline, data_source=None):
    doc = frappe.get_doc("Insights Data Source", data_source or "frappe.cloud")

    args = doc.get_db_credentials()
    db = ibis.mysql.connect(
        host=args.get("host"),
        port=args.get("port"),
        user=args.get("username"),
        password=args.get("password"),
        database=args.get("database_name"),
    )

    translator = QueryPipelineTranslator(query_pipeline, backend=db)
    translated = translator.translate()
    sql = ibis.to_sql(translated, dialect="mysql")

    data = doc.execute_query(sql, return_columns=True)
    return data


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

        return self.query.head(100)

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
        elif step.type == "mutate":
            handler = self.translate_mutate(step)
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
        left = getattr(_, filter_args.column.column_name)
        right = (
            getattr(_, filter_args.value.column_name)
            if isinstance(filter_args.value, dict) and filter_args.value.type == "column"
            else filter_args.value
        )
        operator = self.get_operator(filter_args.operator)
        return lambda query: query.filter(operator(left, right))

    def get_operator(self, operator):
        return {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
        }[operator]

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
            case=ibis.case,
            row_number=ibis.row_number,
        )
        stripped_expression = expression.strip().replace("\n", "").replace("\t", "")
        return frappe.safe_eval(stripped_expression, context)
