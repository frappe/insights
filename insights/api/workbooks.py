import frappe
import ibis
from ibis import _

from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
    execute_ibis_query,
    get_columns_from_schema,
)


@insights_whitelist()
def fetch_query_results(operations, use_live_connection=True):
    results = []
    ibis_query = IbisQueryBuilder().build(operations, use_live_connection)
    if ibis_query is None:
        return

    columns = get_columns_from_schema(ibis_query.schema())
    results = execute_ibis_query(ibis_query)
    results = results.to_dict(orient="records")

    count_query = ibis_query.aggregate(count=_.count())
    count_results = execute_ibis_query(count_query)
    total_count = count_results.values[0][0]

    return {
        "sql": ibis.to_sql(ibis_query),
        "columns": columns,
        "rows": results,
        "total_row_count": int(total_count),
    }


@insights_whitelist()
def download_query_results(operations, use_live_connection=True):
    ibis_query = IbisQueryBuilder().build(operations, use_live_connection)
    if ibis_query is None:
        return

    results = execute_ibis_query(ibis_query, limit=100_00_00)
    return results.to_csv(index=False)


@insights_whitelist()
def get_distinct_column_values(
    operations, column_name, search_term=None, use_live_connection=True
):
    query = IbisQueryBuilder().build(operations, use_live_connection)
    values_query = (
        query.select(column_name)
        .filter(
            getattr(_, column_name).notnull()
            if not search_term
            else getattr(_, column_name).ilike(f"%{search_term}%")
        )
        .distinct()
        .head(20)
    )
    result = execute_ibis_query(values_query, cache=True)
    return result[column_name].tolist()


@insights_whitelist()
def get_columns_for_selection(operations, use_live_connection=True):
    query = IbisQueryBuilder().build(operations, use_live_connection)
    columns = get_columns_from_schema(query.schema())
    return columns


@insights_whitelist()
def get_workbooks():
    return frappe.get_list(
        "Insights Workbook",
        fields=[
            "name",
            "title",
            "owner",
            "creation",
            "modified",
        ],
    )


@insights_whitelist()
def get_share_permissions(workbook_name):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"))

    DocShare = frappe.qb.DocType("DocShare")
    User = frappe.qb.DocType("User")

    share_permissions = (
        frappe.qb.from_(DocShare)
        .left_join(User)
        .on(DocShare.user == User.name)
        .select(
            DocShare.user,
            DocShare.read,
            DocShare.write,
            DocShare.share,
            User.full_name,
        )
        .where(DocShare.share_doctype == "Insights Workbook")
        .where(DocShare.share_name == workbook_name)
        .run(as_dict=True)
    )
    owner = frappe.db.get_value("Insights Workbook", workbook_name, "owner")
    share_permissions.append(
        {
            "user": owner,
            "full_name": frappe.get_value("User", owner, "full_name"),
            "read": 1,
            "write": 1,
        }
    )
    return share_permissions


@insights_whitelist()
def update_share_permissions(workbook_name, permissions):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"))

    perm_exists = lambda user: frappe.db.exists(
        "DocShare",
        {
            "share_doctype": "Insights Workbook",
            "share_name": workbook_name,
            "user": user,
        },
    )

    for permission in permissions:
        if not perm_exists(permission["user"]):
            doc = frappe.new_doc("DocShare")
            doc.update(
                {
                    "share_doctype": "Insights Workbook",
                    "share_name": workbook_name,
                    "user": permission["user"],
                    "read": permission["read"],
                    "write": permission["write"],
                }
            )
            doc.save()
        else:
            doc = frappe.get_doc(
                "DocShare",
                {
                    "share_doctype": "Insights Workbook",
                    "share_name": workbook_name,
                    "user": permission["user"],
                },
            )
            doc.read = permission["read"]
            doc.write = permission["write"]
            doc.save()
