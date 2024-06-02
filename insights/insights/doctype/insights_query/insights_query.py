# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import time

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from ibis import _
from ibis.expr.types import Table as IbisQuery

from insights.insights.doctype.insights_data_source.ibis_utils import (
    IbisQueryBuilder,
    execute_ibis_query,
    get_columns_from_schema,
)


class InsightsQuery(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        execution_time: DF.Float
        last_execution: DF.Datetime | None
        operations: DF.JSON
        results_row_count: DF.Int
        sql: DF.Code | None
        status: DF.Literal[
            "Pending Execution", "Execution Successful", "Execution Failed"
        ]
        title: DF.Data
    # end: auto-generated types

    def on_trash(self):
        # check if this query is being used in other queries
        pass

    def before_validate(self):
        self.title = self.title or self.name
        self.operations = frappe.as_json(frappe.parse_json(self.operations or "[]"))
        query = self.build()
        if query is not None:
            sql = query.compile()
            self.sql = sql
        else:
            self.sql = None

    def build(self) -> IbisQuery:
        operations = frappe.parse_json(self.operations)
        return IbisQueryBuilder().build(operations)

    @frappe.whitelist()
    def fetch_results(self, additional_filters=None):
        results = []
        query = self.build()
        if query is None:
            return

        columns = get_columns_from_schema(query.schema())
        start = time.monotonic()
        try:
            results = execute_ibis_query(query, self.name)
            results = results.fillna("").values.tolist()
            self.db_set(
                {
                    "status": "Execution Successful",
                    "execution_time": flt(time.monotonic() - start, 3),
                    "last_execution": frappe.utils.now(),
                },
                update_modified=False,
                commit=True,
            )

            count_query = query.aggregate(count=_.count())
            count_results = execute_ibis_query(count_query)
            total_count = count_results["count"][0]

        except Exception as e:
            results = []
            frappe.db.rollback()
            frappe.log_error(str(e)[:140])
            self.db_set("status", "Execution Failed", commit=True)
            raise

        finally:
            # custom results for dashboard is cached by dashboard
            if not additional_filters:
                # store the query as a table in duckdb
                pass

        return {
            "sql": self.sql,
            "columns": columns,
            "rows": results,
            "total_row_count": int(total_count),
        }

    @frappe.whitelist()
    def get_distinct_column_values(self, column_name, search_term=None):
        query = self.build()
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

    def reset(self):
        new_query = frappe.new_doc("Insights Query")
        new_query.name = self.name
        new_query.title = self.name.replace("QRY-", "Query ")
        new_query.data_source = self.data_source
        new_query_dict = new_query.as_dict(no_default_fields=True)
        self.update(new_query_dict)
        self.status = "Execution Successful"
