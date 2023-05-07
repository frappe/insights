# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import List, Union

import frappe


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
            label=data.get("label") or "Unnamed",
            type=data.get("type") or "String",
            options=data.get("format_option") or data.get("options") or {},
        )

    @classmethod
    def from_dicts(cls, data: List[dict]) -> List["ResultColumn"]:
        return [cls.from_dict(d) for d in data]
