import frappe


def execute():
    """
    Flatten the columns in the JSON of all assisted queries in the Insights Query doctype.
    """
    queries = frappe.get_all(
        "Insights Query", filters={"is_assisted_query": 1}, fields=["name", "json"]
    )
    for query in queries:
        query_json = frappe.parse_json(query.json)
        query_json.columns = [flatten_if_needed(c) for c in query_json.columns or []]
        query_json.calculations = [flatten_if_needed(c) for c in query_json.calculations or []]
        query_json.measures = [flatten_if_needed(c) for c in query_json.measures or []]
        query_json.dimensions = [flatten_if_needed(c) for c in query_json.dimensions or []]
        query_json.orders = [flatten_if_needed(c) for c in query_json.orders or []]
        frappe.db.set_value("Insights Query", query.name, "json", frappe.as_json(query_json))
        frappe.db.commit()


def flatten_if_needed(column):
    if isinstance(column, dict):
        return column.get("column")
    return column
