# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import List, Union

import frappe
from frappe.utils.caching import redis_cache


class ResultColumn:
    label: str
    type: Union[str, List[str]]
    options: dict = {}

    @staticmethod
    def make(
        label=None, type="String", options=None, query_column=None
    ) -> "ResultColumn":
        if query_column:
            return {
                "label": query_column.get("label") or "Unnamed",
                "type": query_column.get("type") or "String",
                "options": frappe.parse_json(query_column.get("format_option")) or {},
            }
        return {
            "label": label or "Unnamed",
            "type": type or "String",
            "options": options or {},
        }


@redis_cache(ttl=60 * 60 * 24)
def get_data_source_schema_for_prompt(data_source):
    tables = frappe.get_all(
        "Insights Table",
        {"data_source": data_source, "is_query_based": 0},
        pluck="name",
    )
    schema = []
    InsightsTable = frappe.qb.DocType("Insights Table")
    InsightsTableColumn = frappe.qb.DocType("Insights Table Column")
    for table_name in tables:
        query = (
            frappe.qb.from_(InsightsTable)
            .select(
                InsightsTable.table,
                InsightsTableColumn.column,
                InsightsTableColumn.type,
            )
            .left_join(InsightsTableColumn)
            .on(InsightsTable.name == InsightsTableColumn.parent)
            .where(InsightsTable.name == table_name)
            .run(as_dict=True)
        )
        tablename = query[0].table
        columns = [f"{col.column}({col.type})" for col in query]
        schema.append(f"Table '{tablename}' has these columns: {', '.join(columns)}")

    return schema
