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
    def from_args(label, type="String", options=None) -> "ResultColumn":
        return frappe._dict(
            {
                "label": label or "Unnamed",
                "type": type or "String",
                "options": options or {},
            }
        )

    @classmethod
    def from_dict(cls, data: dict) -> "ResultColumn":
        return frappe._dict(
            label=data.get("alias") or data.get("label") or "Unnamed",
            type=data.get("type") or "String",
            options=data.get("format_option")
            or data.get("options")
            or data.get("format_options"),
        )

    @classmethod
    def from_dicts(cls, data: List[dict]) -> List["ResultColumn"]:
        return [cls.from_dict(d) for d in data]


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
