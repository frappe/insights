import frappe


def execute():
    """copy_data_sources from Insights Data Source to Insights Data Source v3"""

    data_sources = frappe.get_all(
        "Insights Data Source",
        filters={"name": ["not in", ["Query Store", "Site DB"]]},
        pluck="name",
    )
    frappe.db.delete("Insights Data Source v3")
    for data_source in data_sources:
        try:
            data_source_doc = frappe.get_doc("Insights Data Source", data_source)
            data_source_v3 = frappe.get_doc(
                {
                    "doctype": "Insights Data Source v3",
                    "creation": data_source_doc.creation,
                    "title": data_source_doc.title,
                    "database_type": data_source_doc.database_type,
                    "database_name": data_source_doc.database_name,
                    "username": data_source_doc.username,
                    "password": data_source_doc.get_password(raise_exception=False),
                    "host": data_source_doc.host,
                    "port": data_source_doc.port,
                    "use_ssl": data_source_doc.use_ssl,
                    "connection_string": data_source_doc.connection_string,
                }
            )
            data_source_v3.insert()
        except Exception as e:
            print(f"Error copying {data_source}: {e}")
