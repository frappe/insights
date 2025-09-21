import frappe


def execute():
    """rename untitled query to query name"""

    query_names = frappe.get_all(
        "Insights Query",
        fields=["name", "title"],
        filters={"title": "Untitled Query"},
    )

    for query in query_names:
        frappe.db.set_value(
            "Insights Query",
            query.name,
            "title",
            query.name.replace("-", " ").replace("QRY", "Query"),
        )
