# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import pathlib
from typing import List, Union

import chardet
import frappe
from frappe.model.base_document import BaseDocument


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
            options=data.get("format_option") or data.get("options") or data.get("format_options"),
        )

    @classmethod
    def from_dicts(cls, data: List[dict]) -> List["ResultColumn"]:
        return [cls.from_dict(d) for d in data]


class DoctypeBase(BaseDocument):
    doctype: str

    @classmethod
    def get_name(cls, *args, **kwargs):
        return frappe.db.exists(cls.doctype, args[0] if len(args) > 0 else kwargs)

    @classmethod
    def exists(cls, *args, **kwargs):
        return cls.get_name(*args, **kwargs) is not None

    @classmethod
    def get_doc(cls, *args, **kwargs) -> "DoctypeBase":
        return frappe.get_doc(cls.doctype, args[0] if len(args) > 0 else kwargs)

    @classmethod
    def get_cached_doc(cls, *args, **kwargs) -> "DoctypeBase":
        return frappe.get_cached_doc(cls.doctype, args[0] if len(args) > 0 else kwargs)

    @classmethod
    def new_doc(cls) -> "DoctypeBase":
        return frappe.new_doc(cls.doctype)


class InsightsChart(DoctypeBase):
    doctype = "Insights Chart"


class InsightsTable(DoctypeBase):
    doctype = "Insights Table"


class InsightsQuery(DoctypeBase):
    doctype = "Insights Query"


class InsightsDataSource(DoctypeBase):
    doctype = "Insights Data Source"


class InsightsSettings:
    @classmethod
    def get(cls, key):
        return frappe.db.get_single_value("Insights Settings", key)


def detect_encoding(file_path: str):
    file_path: pathlib.Path = pathlib.Path(file_path)
    with open(file_path, "rb") as file:
        result = chardet.detect(file.read())
    return result["encoding"]
