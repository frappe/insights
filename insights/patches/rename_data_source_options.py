import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Data Source"):
        return

    DataSource = frappe.qb.DocType("Insights Data Source")
    (
        frappe.qb.update(DataSource)
        .set(DataSource.database_type, "MariaDB")
        .set(DataSource.source_type, "Site Database")
        .where(DataSource.database_type == "Query Store")
        .run()
    )
    (
        frappe.qb.update(DataSource)
        .set(DataSource.source_type, "Site Database")
        .where(
            DataSource.name == "Demo Data"
            or (DataSource.source_type == "Application Database")
        )
        .run()
    )
    (
        frappe.qb.update(DataSource)
        .set(DataSource.source_type, "Database")
        .where(
            (DataSource.source_type.isnull())
            or (DataSource.source_type == "Remote Database")
        )
        .run()
    )
