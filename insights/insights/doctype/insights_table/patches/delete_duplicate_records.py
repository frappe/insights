import frappe


def execute():
    delete_duplicate_records()


def delete_duplicate_records():
    """
    Delete records in Insights Table with duplicate
    table, data_source, and is_query_based.
    """
    data_sources = frappe.get_all("Insights Data Source", pluck="name")
    for data_source in data_sources:
        tables = frappe.get_all(
            "Insights Table",
            filters={"data_source": data_source},
            fields=["table", "is_query_based"],
            as_list=True,
        )
        for table in tables:
            duplicates = frappe.get_all(
                "Insights Table",
                filters={
                    "table": table[0],
                    "is_query_based": table[1],
                    "data_source": data_source,
                },
                pluck="name",
            )
            if len(duplicates) > 1:
                frappe.db.sql(
                    "DELETE FROM `tabInsights Table` WHERE name IN %(duplicates)s",
                    {"duplicates": tuple(duplicates[1:])},
                )
