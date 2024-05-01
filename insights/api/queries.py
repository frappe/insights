import frappe
import ibis
from ibis import BaseBackend, _
from ibis import selectors as s
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
def execute_query_pipeline(data_source, query_pipeline):
    doc = frappe.get_doc("Insights Data Source", data_source)

    conn: BaseBackend = doc.get_ibis_connection()
    translator = QueryTranslator(query_pipeline, backend=conn)
    query = translator.translate()
    data: DataFrame = conn.execute(query, limit=100)
    total_row_count = conn.execute(query.count())
    return {
        "columns": get_columns_from_dataframe(data),
        "rows": data.fillna("").to_dict(orient="records"),
        "total_row_count": int(total_row_count),
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


@frappe.whitelist()
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


@frappe.whitelist()
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


@frappe.whitelist()
def execute_analytical_query(model, query):
    query = _dict(query)
    model = _dict(model)
    dataset_by_name = {dataset.name: dataset for dataset in model.datasets}

    # first find all the dataset names from the columns referenced in the query
    dataset_names = set()
    for column in query.measures + query.dimensions:
        dataset_names.add(column.dataset)

    # make dataset objects
    datasets = {}
    for dataset_name in dataset_names:
        dataset = dataset_by_name.get(dataset_name)
        doc = frappe.get_doc("Insights Data Source", dataset.data_source)
        conn: BaseBackend = doc.get_ibis_connection()
        translator = QueryTranslator(dataset.operations, backend=conn)
        expression = translator.translate()
        datasets[dataset_name] = expression

    # join the datasets based on model.relationships
    joined_dataset = None
    for dataset_name, dataset in datasets.items():
        joined_dataset = dataset
        for relationship in model.relationships:
            if dataset_name == relationship.leftDataset:
                rightDataset = datasets[relationship.rightDataset]
                left_column = getattr(dataset, relationship.leftColumn)
                right_column = getattr(rightDataset, relationship.rightColumn)
                joined_dataset = dataset.join(
                    rightDataset, left_column == right_column, how="left"
                ).select(~s.endswith("right"))
            if dataset_name == relationship.rightDataset:
                leftDataset = datasets[relationship.leftDataset]
                left_column = getattr(leftDataset, relationship.leftColumn)
                right_column = getattr(dataset, relationship.rightColumn)
                joined_dataset = leftDataset.join(
                    dataset, left_column == right_column, how="left"
                ).select(~s.endswith("right"))

    # group by the dimensions
    group_by_columns = [
        getattr(joined_dataset, dimension.column_name) for dimension in query.dimensions
    ]

    # aggregate the measures
    aggregates = {}
    for measure in query.measures:
        aggregates[measure.column_name] = getattr(joined_dataset, measure.column_name).sum()

    # apply the group by and aggregates
    query = joined_dataset.aggregate(**aggregates, by=group_by_columns)

    # # apply the order by
    if query.order_by:
        column = getattr(joined_dataset, query.order_by.column)
        column = column.asc() if query.order_by.direction == "asc" else column.desc()
        query = query.order_by(column)

    # # apply the limit
    if query.limit:
        query = query.limit(query.limit)

    # execute the query
    data: DataFrame = query.head(100).execute()
    return {
        "columns": get_columns_from_dataframe(data),
        "rows": data.to_dict(orient="records"),
        "sql": ibis.to_sql(query),
    }


@frappe.whitelist()
def execute_analysis_query(model, query):
    model = _dict(model)
    model_query = model.queries[0]
    doc = frappe.get_doc("Insights Data Source", model_query.dataSource)
    conn: BaseBackend = doc.get_ibis_connection()
    translator = QueryTranslator(model_query.operations, backend=conn)
    expression = translator.translate()
    base_data = expression

    # TODO: add calculated dimensions & measures to the model

    query = _dict(query)
    rows = [row.column_name for row in query["rows"]]
    columns = [column.column_name for column in query["columns"]]
    values = [value.column_name for value in query["values"] if value.column_name != "count"]

    if rows and columns and values:
        expression = base_data.pivot_wider(
            id_cols=rows,
            names_from=columns,
            values_from=values,
            values_agg="sum",
            values_fill=0,
        )
    elif rows and columns:
        # default to count if no values are provided
        expression = base_data.pivot_wider(
            id_cols=rows,
            names_from=columns,
            values_from=rows[0],
            values_agg="count",
            values_fill=0,
        )
    elif rows and values:
        group_by_columns = [getattr(base_data, row) for row in rows]
        aggregates = {value: getattr(base_data, value).sum() for value in values}
        expression = base_data.aggregate(**aggregates, by=group_by_columns)
    elif rows:
        expression = base_data.aggregate(count=getattr(base_data, rows[0]).count(), by=rows)
    elif columns and values:
        frappe.throw("Columns and Values without Rows is not supported")
    elif columns:
        frappe.throw("Columns without Rows is not supported")
    elif values:
        frappe.throw("Values without Rows is not supported")

    # execute the query
    data: DataFrame = expression.head(100).execute()
    return {
        "columns": get_columns_from_dataframe(data),
        "rows": data.to_dict(orient="records"),
        "sql": ibis.to_sql(expression),
    }


@frappe.whitelist()
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
        "columns": get_columns_from_dataframe(data),
        "rows": data.to_dict(orient="records"),
        "sql": ibis.to_sql(query),
    }


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
        # elif operation.type == "group_by":
        #     handler = self.translate_group_by(operation)
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
                self.translate_col_expression(filter_args.expression)
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
        new_name = mutate_args.new_name
        # data_type = mutate_args.data_type
        new_column = self.translate_col_expression(mutate_args.mutation)
        return lambda query: query.mutate(**{new_name: new_column})

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
