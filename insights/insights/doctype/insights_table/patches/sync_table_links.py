import click
import frappe

from insights.insights.doctype.insights_data_source.sources.frappe_db import FrappeDB


def execute():
    data_sources = frappe.get_all(
        "Insights Data Source",
        {
            "database_type": "MariaDB",
            "status": "Active",
        },
        pluck="name",
    )
    for data_source in data_sources:
        doc = frappe.get_doc("Insights Data Source", data_source)
        try:
            if not isinstance(doc._db, FrappeDB) and not doc.is_site_db:
                click.echo(f"Skipping {data_source} as it is not a MariaDB data source")
                continue
            click.echo(f"Syncing tables for {data_source}")
            with doc._db.engine.begin() as connection:
                doc._db.table_factory.db_conn = connection
                table_names = doc._db.table_factory.get_columns_by_tables().keys()
                with click.progressbar(list(table_names)) as tables:
                    for table_name in tables:
                        table = get_table(table_name, data_source)
                        if not table:
                            continue
                        clear_table_links(table.name)
                        table_links = doc._db.table_factory.get_table_links(table.label)
                        insert_table_links(table.name, table_links)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            print(f"Failed to sync tables for {data_source}: {e}")


def get_table(table_name, data_source):
    return frappe.db.get_value(
        "Insights Table",
        {"table": table_name, "data_source": data_source},
        ["name", "label"],
        as_dict=True,
    )


def clear_table_links(table_docname):
    frappe.db.delete("Insights Table Link", {"parent": table_docname})


def insert_table_links(table_docname, table_links):
    for idx, table_link in enumerate(table_links):
        frappe.get_doc(
            {
                "doctype": "Insights Table Link",
                "idx": idx + 1,
                "parent": table_docname,
                "parenttype": "Insights Table",
                "parentfield": "table_links",
                "primary_key": table_link.get("primary_key"),
                "foreign_key": table_link.get("foreign_key"),
                "foreign_table": table_link.get("foreign_table"),
                "foreign_table_label": table_link.get("foreign_table_label"),
                "cardinality": table_link.get("cardinality"),
            }
        ).db_insert(ignore_if_duplicate=True)
