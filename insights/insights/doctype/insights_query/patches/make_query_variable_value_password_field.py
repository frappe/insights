import frappe


def execute():
    """make_query_variable_value_password_field"""

    if not frappe.db.exists("DocType", "Insights Query Variable"):
        return

    query_variables = frappe.get_all(
        "Insights Query Variable", fields=["name", "parent", "variable_value"]
    )
    frappe.reload_doc("insights", "doctype", "insights_query")
    frappe.reload_doc("insights", "doctype", "insights_query_variable")
    for query_variable in query_variables:
        doc = frappe.get_doc("Insights Query", query_variable["parent"])
        for var in doc.variables:
            if var.name == query_variable["name"]:
                var.variable_value = query_variable["variable_value"]
                doc.save()
                break
