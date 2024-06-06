# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe


import frappe
import frappe.utils
import ibis
from frappe.model.document import Document
from ibis import _

from insights.insights.doctype.insights_data_source.ibis_utils import (
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
        queries: DF.JSON | None
        title: DF.Data
    # end: auto-generated types

    def before_save(self):
        self.title = self.title or get_title(self.name)
        queries = frappe.parse_json(self.queries)
        for query in queries:
            if query["operations"]:
                ibis_query = IbisQueryBuilder().build(query["operations"])
                query["sql"] = ibis_query.compile()
            else:
                query["sql"] = None

        self.queries = frappe.as_json(queries)
        self.charts = frappe.as_json(frappe.parse_json(self.charts))
        self.dashboards = frappe.as_json(frappe.parse_json(self.dashboards))


@frappe.whitelist()
def fetch_query_results(operations):
    results = []
    ibis_query = IbisQueryBuilder().build(operations)
    if ibis_query is None:
        return

    columns = get_columns_from_schema(ibis_query.schema())
    results = execute_ibis_query(ibis_query)
    results = results.values.tolist()

    count_query = ibis_query.aggregate(count=_.count())
    count_results = execute_ibis_query(count_query)
    total_count = count_results["count"][0]

    return {
        "sql": ibis.to_sql(ibis_query),
        "columns": columns,
        "rows": results,
        "total_row_count": int(total_count),
    }


@frappe.whitelist()
def get_distinct_column_values(operations, column_name, search_term=None):
    query = IbisQueryBuilder().build(operations)
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
    result = execute_ibis_query(values_query)
    return result[column_name].tolist()


def get_title(name):
    number = name.split("-")[1]
    return f"Workbook {frappe.utils.cint(number)}"
