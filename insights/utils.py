# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import List, Union

import frappe


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
