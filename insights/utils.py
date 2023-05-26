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
def get_data_source_schema(data_source, **filters):
    tables = frappe.get_all(
        "Insights Table",
        {"data_source": data_source, **filters},
        pluck="name",
    )
    InsightsTable = frappe.qb.DocType("Insights Table")
    InsightsTableColumn = frappe.qb.DocType("Insights Table Column")
    data = (
        frappe.qb.from_(InsightsTable)
        .select(
            InsightsTable.name,
            InsightsTable.table,
            InsightsTableColumn.column,
            InsightsTableColumn.type,
            InsightsTableColumn.modified,
            InsightsTable.metadata,
        )
        .left_join(InsightsTableColumn)
        .on(InsightsTable.name == InsightsTableColumn.parent)
        .where(InsightsTable.name.isin(tables))
        .run(as_dict=True)
    )
    schema = {}
    for row in data:
        if row.table not in schema:
            metadata = frappe.parse_json(row.metadata)
            schema[row.table] = {
                "name": row.name,
                "table": row.table,
                "columns": [],
                "modified": row.modified,
                "row_count": metadata.get("row_count") or 0,
            }
        schema[row.table]["columns"].append(
            {
                "column": row.column,
                "type": row.type,
            }
        )

    return list(schema.values())


@redis_cache(ttl=60 * 60 * 24 * 7)
def get_data_source_dialect(data_source):
    data_source = frappe.get_cached_doc("Insights Data Source", data_source)
    return data_source.db.engine.dialect.name
