# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _dict
from frappe.model.document import Document


class InsightsTableColumn(Document):
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
