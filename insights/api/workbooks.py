import frappe
import ibis
from ibis import _

from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
    execute_ibis_query,
    get_columns_from_schema,
)
from insights.utils import DocShare


@insights_whitelist()
def fetch_query_results(operations, limit=100, use_live_connection=True):
    results = []
    ibis_query = IbisQueryBuilder().build(operations, use_live_connection)
    if ibis_query is None:
        return

    columns = get_columns_from_schema(ibis_query.schema())
    results, time_taken = execute_ibis_query(
        ibis_query, limit=limit, cache_expiry=60 * 10
    )
    results = results.to_dict(orient="records")

    return {
        "sql": ibis.to_sql(ibis_query),
        "columns": columns,
        "rows": results,
        "time_taken": time_taken,
    }


@insights_whitelist()
def fetch_query_results_count(operations, use_live_connection=True):
    ibis_query = IbisQueryBuilder().build(operations, use_live_connection)
    if ibis_query is None:
        return

    count_query = ibis_query.aggregate(count=_.count())
    count_results, time_taken = execute_ibis_query(count_query, cache_expiry=60 * 5)
    total_count = count_results.values[0][0]
    return int(total_count)


@insights_whitelist()
def download_query_results(operations, use_live_connection=True):
    ibis_query = IbisQueryBuilder().build(operations, use_live_connection)
    if ibis_query is None:
        return

    results, time_taken = execute_ibis_query(ibis_query, cache=False, limit=10_00_000)
    return results.to_csv(index=False)


@insights_whitelist()
def get_distinct_column_values(
    operations, column_name, search_term=None, use_live_connection=True, limit=20
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
        .head(limit)
    )
    result, time_taken = execute_ibis_query(values_query, cache_expiry=24 * 60 * 60)
    return result[column_name].tolist()


@insights_whitelist()
def get_columns_for_selection(operations, use_live_connection=True):
    query = IbisQueryBuilder().build(operations, use_live_connection)
    columns = get_columns_from_schema(query.schema())
    return columns


@insights_whitelist()
def get_workbooks(search_term=None, limit=100):
    workbooks = frappe.get_list(
        "Insights Workbook",
        or_filters={
            "owner": ["like", f"%{search_term}%" if search_term else "%"],
            "title": ["like", f"%{search_term}%" if search_term else "%"],
        },
        fields=[
            "name",
            "title",
            "owner",
            "creation",
            "modified",
        ],
        limit=limit,
    )
    # FIX: figure out how to use frappe.qb while respecting permissions
    # TODO: use frappe.qb to get the view count
    workbook_names = [workbook["name"] for workbook in workbooks]
    workbook_views = frappe.get_all(
        "View Log",
        filters={
            "reference_doctype": "Insights Workbook",
            "reference_name": ["in", workbook_names],
        },
        fields=["reference_name", "name"],
    )
    for workbook in workbooks:
        views = [
            view
            for view in workbook_views
            if str(view["reference_name"]) == str(workbook["name"])
        ]
        workbook["views"] = len(views)

    for workbook in workbooks:
        organization_has_access = frappe.db.exists(
            "DocShare",
            {
                "share_doctype": "Insights Workbook",
                "share_name": workbook["name"],
                "everyone": 1,
                "read": 1,
            },
        )
        if organization_has_access:
            workbook["shared_with_organization"] = True
            continue

        shared_with = frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Workbook",
                "share_name": workbook["name"],
                "user": ["!=", workbook["owner"]],
                "read": 1,
            },
            pluck="user",
        )
        workbook["shared_with"] = shared_with

    return workbooks


@insights_whitelist()
def get_share_permissions(workbook_name):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"))

    DocShare = frappe.qb.DocType("DocShare")
    User = frappe.qb.DocType("User")

    user_permissions = (
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
    user_permissions.append(
        {
            "user": owner,
            "full_name": frappe.get_value("User", owner, "full_name"),
            "read": 1,
            "write": 1,
        }
    )

    public_docshare = frappe.db.get_value(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": workbook_name,
            "everyone": 1,
        },
        fieldname=["read", "write"],
        as_dict=True,
    )
    organization_access = None
    if public_docshare:
        organization_access = "edit" if public_docshare["write"] else "view"

    return {
        "user_permissions": user_permissions,
        "organization_access": organization_access,
    }


@insights_whitelist()
def update_share_permissions(
    workbook_name, user_permissions, organization_access: str | None = None
):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"))

    for permission in user_permissions:
        doc = DocShare.get_or_create_doc(
            share_doctype="Insights Workbook",
            share_name=workbook_name,
            user=permission["user"],
        )
        doc.read = permission["read"]
        doc.write = permission["write"]
        doc.notify_by_email = 0
        doc.save()

    public_docshare = DocShare.get_or_create_doc(
        share_doctype="Insights Workbook",
        share_name=workbook_name,
        everyone=1,
    )
    if organization_access:
        public_docshare.read = 1
        public_docshare.write = organization_access == "edit"
        public_docshare.notify_by_email = 0
        public_docshare.save()
    elif public_docshare.name:
        public_docshare.delete()


@frappe.whitelist(allow_guest=True)
def fetch_shared_chart_data(chart_name: str):
    workbooks = frappe.get_all(
        "Insights Workbook",
        filters={"charts": ["like", f"%{chart_name}%"]},
        pluck="name",
    )
    if not workbooks:
        frappe.throw("Chart not found")

    workbook = frappe.get_doc("Insights Workbook", workbooks[0])
    return workbook.get_shared_chart_data(chart_name)
