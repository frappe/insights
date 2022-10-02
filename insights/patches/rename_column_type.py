import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query Column"):
        return

    QueryColumn = frappe.qb.DocType("Insights Query Column")
    replace_map = {
        "Varchar": "String",
        "Int": "Integer",
        "Float": "Decimal",
        "Timestamp": "Datetime",
        "Longtext": "Text",
    }
    for old, new in replace_map.items():
        (
            frappe.qb.update(QueryColumn)
            .set(QueryColumn.type, new)
            .where(QueryColumn.type == old)
            .run()
        )
