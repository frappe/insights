# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe


import frappe
import frappe.utils
import ibis
from frappe.model.document import Document
from ibis import _

from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
    execute_ibis_query,
    get_columns_from_schema,
)


class InsightsWorkbook(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        charts: DF.JSON | None
        dashboards: DF.JSON | None
        name: DF.Int | None
        queries: DF.JSON | None
        title: DF.Data
    # end: auto-generated types

    def before_save(self):
        self.title = self.title or f"Workbook {frappe.utils.cint(self.name)}"
        # fix: json field value cannot be a list (see: base_document.py:get_valid_dict)
        self.queries = frappe.as_json(frappe.parse_json(self.queries))
        self.charts = frappe.as_json(frappe.parse_json(self.charts))
        self.dashboards = frappe.as_json(frappe.parse_json(self.dashboards))


@frappe.whitelist()
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


@frappe.whitelist()
def download_query_results(operations, use_live_connection=True):
    ibis_query = IbisQueryBuilder().build(operations, use_live_connection)
    if ibis_query is None:
        return

    results = execute_ibis_query(ibis_query, limit=100_00_00)
    return results.to_csv(index=False)


@frappe.whitelist()
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


@frappe.whitelist()
def get_columns_for_selection(operations, use_live_connection=True):
    query = IbisQueryBuilder().build(operations, use_live_connection)
    columns = get_columns_from_schema(query.schema())
    return columns


@frappe.whitelist()
def get_workbooks():
    return frappe.get_list(
        "Insights Workbook", fields=["name", "title", "owner", "creation", "modified"]
    )


@frappe.whitelist()
def get_share_permissions(workbook_name):
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


@frappe.whitelist()
def update_share_permissions(workbook_name, permissions):
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
