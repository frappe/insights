import frappe
import ibis
from ibis import BaseBackend, _
from ibis import selectors as s
from ibis.expr.datatypes import DataType
from pandas import DataFrame

from insights.api.telemetry import track
from insights.decorators import check_role
from insights.insights.doctype.insights_query.utils import infer_type_from_list
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
def execute_query_pipeline(data_source, query_pipeline, limit=100):
    doc = frappe.get_doc("Insights Data Source", data_source)

    conn: BaseBackend = doc.get_ibis_connection()
    translator = QueryTranslator(query_pipeline, backend=conn)
    query = translator.translate()
    sql = ibis.to_sql(query)
    data: DataFrame = conn.execute(query, limit=limit)
    total_row_count = conn.execute(query.count()) if limit else data.shape[0]
    return {
        "sql": sql,
        "columns": get_columns_from_schema(query.schema()),
        "rows": data.fillna("").to_dict(orient="records"),
        "total_row_count": int(total_row_count),
    }


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
    if dtype.is_decimal():
        return "Decimal"
    if dtype.is_timestamp():
        return "Datetime"
    if dtype.is_date():
        return "Date"
    if dtype.is_time():
        return "Time"
    frappe.throw(f"Cannot infer data type for: {dtype}")


class QueryTranslator:
    def __init__(self, query_operations, backend=None):
        self.query = None
        self.db_backend = backend
        self.query_operations = query_operations

    def translate(self):
        self.query = None
        for operation in self.query_operations:
            handler = self.get_operation_handler(operation)
            self.query = handler(self.query)
        return self.query

    def get_table(self, table_name):
        # VUL: Any table can be accessed
        return self.db_backend.table(table_name)

    def get_operation_handler(self, operation):
        operation = _dict(operation)
        handler = lambda query: query
        if operation.type == "source":
            handler = self.translate_source(operation)
        elif operation.type == "join":
            handler = self.translate_join(operation)
        elif operation.type == "filter":
            handler = self.translate_filter(operation)
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
        table = self.get_table(source_args.table.table_name)
        return lambda _: table

    def translate_join(self, join_args):
        right_table = self.get_table(join_args.table.table_name)
        left_column = getattr(_, join_args.left_column.column_name)
        right_column = getattr(right_table, join_args.right_column.column_name)
        join_on = left_column == right_column
        join_type = join_args.join_type
        join_type = "outer" if join_type == "full" else join_type
        return lambda query: query.join(right_table, join_on, how=join_type).select(
            ~s.endswith("right")
        )

    def translate_filter(self, filter_args):
        if hasattr(filter_args, "expression") and filter_args.expression:
            return lambda query: query.filter(
                self.evaluate_expression(filter_args.expression.expression)
            )

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
            "in": lambda x, y: x.isin(y),
            "not_in": lambda x, y: ~x.isin(y),
            "is_set": lambda x, y: x.notnull(),
            "is_not_set": lambda x, y: x.isnull(),
            "contains": lambda x, y: x.like(y),
            "not_contains": lambda x, y: ~x.like(y),
            "starts_with": lambda x, y: x.like(f"{y}%"),
            "ends_with": lambda x, y: x.like(f"%{y}"),
            "between": lambda x, y: x.between(y[0], y[1]),
            "within": lambda x, y: handle_timespan(x, y),
        }[operator]

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
        new_column = self.evaluate_expression(mutate_args.mutation.expression).cast(dtype)
        return lambda query: query.mutate(**{new_name: new_column})

    def translate_summary(self, summarize_args):
        measures = summarize_args.measures
        dimensions = summarize_args.dimensions
        aggregates = {measure.column_name: self.translate_measure(measure) for measure in measures}
        group_bys = [self.translate_dimension(dimension) for dimension in dimensions]
        return lambda query: query.aggregate(**aggregates, by=group_bys)

    def translate_order_by(self, order_by_args):
        column = getattr(_, order_by_args.column.column_name)
        column = column.asc() if order_by_args.direction == "asc" else column.desc()
        return lambda query: query.order_by(column)

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
        if column.type() not in ["date", "timestamp"]:
            column = column.cast("date")
        return column.strftime(format_str[granularity])

    def evaluate_expression(self, expression):
        context = frappe._dict(
            q=_,
            columns=ibis.selectors.c,
            case=ibis.case,
            row_number=ibis.row_number,
        )
        stripped_expression = expression.strip().replace("\n", "").replace("\t", "")
        return frappe.safe_eval(stripped_expression, context)


# unused methods


def get_distinct_column_values(data_source, query_pipeline, column_name, search_term=None):
    doc = frappe.get_doc("Insights Data Source", data_source)

    conn = doc.get_ibis_connection()
    translator = QueryTranslator(query_pipeline, backend=conn)
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


def get_min_max(data_source, query_pipeline, column_name):
    doc = frappe.get_doc("Insights Data Source", data_source)

    conn = doc.get_ibis_connection()
    translator = QueryTranslator(query_pipeline, backend=conn)
    query = translator.translate()
    values_query = query.select(column_name).aggregate(
        min=getattr(_, column_name).min(), max=getattr(_, column_name).max()
    )
    sql = ibis.to_sql(values_query)
    values = doc.execute_query(sql)
    return values[0]


def get_measure_values(model, measures):
    model = _dict(model)
    model_query = model.queries[0]
    doc = frappe.get_doc("Insights Data Source", model_query.dataSource)
    conn: BaseBackend = doc.get_ibis_connection()
    translator = QueryTranslator(model_query.operations, backend=conn)
    expression = translator.translate()

    _measures = {}
    for measure in measures:
        agg = measure.get("aggregation", "sum")
        column = measure.get("column_name")
        if agg == "count":
            _measures[column] = expression.count()
        elif agg == "sum":
            _measures[column] = getattr(expression, column).sum()
        else:
            frappe.throw(f"Aggregation {agg} is not supported")

    query = expression.aggregate(**_measures, by=[])
    data: DataFrame = query.head(100).execute()
    return {
        "columns": get_columns_from_schema(query.schema()),
        "rows": data.fillna("").to_dict(orient="records"),
        "sql": ibis.to_sql(query),
    }


def get_columns_from_dataframe(df):
    type_map = {
        "int64": "Integer",
        "float64": "Decimal",
        "object": "String",
        "datetime64": "Datetime",
        "bool": "Boolean",
    }
    columns = []
    sample = df.head(100)
    for col in df.columns:
        inferred_type = type_map.get(df[col].dtype.name, "String")
        if inferred_type == "String":
            inferred_type = infer_type_from_list(sample[col])
        columns.append({"name": col, "type": inferred_type})
    return columns
