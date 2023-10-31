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
    User = frappe.qb.DocType("User")
    return (
        frappe.qb.from_(Query)
        .left_join(QueryChart)
        .on(QueryChart.query == Query.name)
        .left_join(User)
        .on(Query.owner == User.name)
        .select(
            Query.name,
            Query.title,
            Query.status,
            Query.is_assisted_query,
            Query.is_native_query,
            Query.data_source,
            Query.creation,
            Query.owner,
            User.full_name.as_("owner_name"),
            User.user_image.as_("owner_image"),
            QueryChart.chart_type,
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
def apply_pivot_transform(data, rows, columns, values):
    import pandas as pd

    # create a dataframe
    df = pd.DataFrame(data[1:], columns=data[0])

    # create a pivot table
    pivot = pd.pivot_table(
        df, index=rows, columns=columns, values=values, sort=False, fill_value=0, aggfunc="sum"
    )
    csv = pivot.to_csv(sep=";")

    out = []
    _rows = csv.split("\n")
    for row in _rows:
        out.append(row.split(";"))
    return out
