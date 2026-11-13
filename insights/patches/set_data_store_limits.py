import frappe


def execute():
    # migrate does not write a new Single field's default; 0 already meant "use the default"
    if not frappe.db.count("Singles", {"doctype": "Insights Settings"}):
        return  # an unsaved Single loads its defaults

    for field, default in (("max_records_to_sync", 1_000_000), ("max_memory_usage", 512)):
        if not frappe.db.get_single_value("Insights Settings", field):
            frappe.db.set_single_value("Insights Settings", field, default)
