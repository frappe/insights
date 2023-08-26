import frappe
from frappe.model.naming import NamingSeries, _format_autoname, set_new_name


def execute():
    """change_data_source_naming_series"""

    # currently data sources are named by the `title` user has given
    # this causes a problem when exporting and importing queries
    # since the data source name (in some case) should be anonymous while exporting
    # so, we are changing the naming series of data source to `DSO-<###>`

    reserved_names = ["Query Store", "Site DB", "Demo Data"]
    data_sources = frappe.get_all(
        "Insights Data Source",
        filters={"name": ["not in", reserved_names]},
        fields=["name", "title"],
        order_by="creation asc",
    )
    name_by_title = {}
    for data_source in data_sources:
        doc = frappe.get_doc("Insights Data Source", data_source.name)
        doc.set_new_name(force=True)
        frappe.rename_doc("Insights Data Source", data_source.name, doc.name, force=True)
        name_by_title[data_source.title] = doc.name

    # update the data source title in dashboard items
    dashboard_items = frappe.get_all(
        "Insights Dashboard Item",
        fields=["name", "options"],
        filters={"options": ["like", "%data_source%"]},
    )
    for dashboard_item in dashboard_items:
        options = frappe.parse_json(dashboard_item.options)
        if "data_source" in options["column"]:
            title = options["column"]["data_source"]
            if title not in reserved_names:
                options["column"]["data_source"] = name_by_title[title]
                frappe.db.set_value(
                    "Insights Dashboard Item",
                    dashboard_item.name,
                    "options",
                    frappe.as_json(options),
                )
