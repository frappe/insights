# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe import _dict
from frappe.model.document import Document
from ibis import Schema


class InsightsTableColumn(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        column: DF.Data
        label: DF.Data
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        type: DF.Literal[
            "Integer",
            "Long Int",
            "Decimal",
            "Text",
            "Long Text",
            "Date",
            "Datetime",
            "Time",
            "String",
        ]
    # end: auto-generated types

    @staticmethod
    def from_ibis_schema(schema: Schema):
        from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
            to_insights_type,
        )

        return [
            _dict(
                column=column,
                label=column,
                type=to_insights_type(datatype),
            )
            for column, datatype in schema.items()
        ]

    @classmethod
    def from_dict(cls, obj):
        column = _dict(
            label=obj.get("alias") or obj.get("label") or obj.get("column"),
            column=obj.get("alias") or obj.get("label") or obj.get("column"),
            type=obj.get("type") or "String",
        )
        if not column.label:
            frappe.throw("Column Label is required")
        if not column.column:
            frappe.throw("Column Name is required")
        return column

    @classmethod
    def from_dicts(cls, objs):
        return [cls.from_dict(obj) for obj in objs]
