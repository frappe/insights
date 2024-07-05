import frappe

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
        .groupby(
            Query.name,
            User.full_name.as_("owner_name"),
            User.user_image.as_("owner_image"),
            QueryChart.chart_type,
            DataSource.title.as_("data_source_title"),
        )
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
