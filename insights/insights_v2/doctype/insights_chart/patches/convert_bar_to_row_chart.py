import frappe


def execute():
    """convert_bar_to_row_chart"""

    insights_charts = frappe.get_all(
        "Insights Chart",
        filters={"options": ["like", "%invertAxis%"]},
        fields=["name", "options"],
    )
    for insights_chart in insights_charts:
        doc = frappe.get_doc("Insights Chart", insights_chart.name)
        options = frappe.parse_json(doc.options)
        if options.get("invertAxis"):
            options["invertAxis"] = False
            doc.options = frappe.as_json(options)
            doc.chart_type = "Row"
            doc.save()

    insights_dashboard_item = frappe.get_all(
        "Insights Dashboard Item",
        filters={"options": ["like", "%invertAxis%"]},
        fields=["name", "options"],
    )
    for insights_dashboard in insights_dashboard_item:
        doc = frappe.get_doc("Insights Dashboard Item", insights_dashboard.name)
        options = frappe.parse_json(doc.options)
        if options.get("invertAxis"):
            options["invertAxis"] = False
            doc.options = frappe.as_json(options)
            doc.item_type = "Row"
            doc.save()
