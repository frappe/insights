# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import pathlib
from typing import List, Union

import chardet
import frappe
import pandas as pd
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
    def new_doc(cls, **kwargs) -> "DoctypeBase":
        new_doc = frappe.new_doc(cls.doctype)
        new_doc.update(kwargs)
        return new_doc

    @classmethod
    def get_or_create_doc(cls, *args, **kwargs) -> "DoctypeBase":
        name = cls.get_name(*args, **kwargs)
        if name:
            return cls.get_doc(name)
        else:
            return cls.new_doc(**kwargs)

    @classmethod
    def get_value(cls, *args, **kwargs):
        return frappe.db.get_value(cls.doctype, *args, **kwargs)

    @classmethod
    def delete_doc(cls, name):
        return frappe.delete_doc(cls.doctype, name)


class InsightsChart(DoctypeBase):
    doctype = "Insights Chart"


class InsightsTable(DoctypeBase):
    doctype = "Insights Table"


class InsightsQuery(DoctypeBase):
    doctype = "Insights Query"


class InsightsDataSource(DoctypeBase):
    doctype = "Insights Data Source"


class InsightsQueryResult(DoctypeBase):
    doctype = "Insights Query Result"


class InsightsSettings:
    @classmethod
    def get(cls, key):
        return frappe.db.get_single_value("Insights Settings", key)


def detect_encoding(file_path: str):
    file_path: pathlib.Path = pathlib.Path(file_path)
    with open(file_path, "rb") as file:
        result = chardet.detect(file.read())
    return result["encoding"]


def anonymize_data(df, columns_to_anonymize, prefix_by_column=None):
    """
    Anonymizes the data in the specified columns of a DataFrame.

    Args:
        df (pandas.DataFrame): The DataFrame containing the data to be anonymized.
        columns_to_anonymize (list): A list of column names to be anonymized.
        prefix_by_column (dict, optional): A dictionary mapping column names to prefixes.
            If provided, the anonymized values will be prefixed with the corresponding value.
            Defaults to None.

    Returns:
        pandas.DataFrame: The DataFrame with the anonymized data.
    """
    for column in columns_to_anonymize:
        codes = pd.factorize(df[column])[0] + 1
        prefix = prefix_by_column[column] if prefix_by_column else column
        df[column] = prefix + pd.Series(codes).astype(str)

    return df
