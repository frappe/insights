from frappe import _dict

SOURCE_STATUS = _dict(
    {
        "Active": "Active",
        "Inactive": "Inactive",
    }
)


COLUMN_TYPES = {
    "Integer": ("int", "11"),
    "Long Int": ("bigint", "20"),
    "Decimal": ("decimal", "21,9"),
    "Text": ("text", ""),
    "Long Text": ("longtext", ""),
    "Date": ("date", ""),
    "Datetime": ("datetime", "6"),
    "Time": ("time", "6"),
    "Text": ("text", ""),
    "String": ("varchar", "255"),
}
