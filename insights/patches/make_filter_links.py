import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Dashboard Item"):
        return

    dashboard_items = frappe.get_all(
        "Insights Dashboard Item",
        filters={"item_type": "Chart"},
        fields=["chart", "parent", "chart_filters"],
    )

    filters_by_filter_name = {}
    for chart_item in dashboard_items:
        chart_filters = frappe.parse_json(chart_item.chart_filters) or []
        for chart_filter in chart_filters:
            chart_filter = frappe._dict(chart_filter)
            filter_item_name = frappe.db.get_value(
                "Insights Dashboard Item",
                {
                    "parent": chart_item.parent,
                    "item_type": "Filter",
                    "filter_label": chart_filter.filter.get("label"),
                },
                "name",
            )
            if not filter_item_name:
                continue
            filters_by_filter_name.setdefault(filter_item_name, {})
            filters_by_filter_name[filter_item_name].setdefault(
                chart_item.chart,
                {
                    "label": chart_filter.column.get("label"),
                    "table": chart_filter.column.get("value").split(".")[0],
                    "column": chart_filter.column.get("value").split(".")[1],
                    "value": chart_filter.column.get("value"),
                },
            )

    for filter_name, filter_value in filters_by_filter_name.items():
        frappe.db.set_value(
            "Insights Dashboard Item",
            filter_name,
            "filter_links",
            frappe.as_json(filter_value),
        )

    # update chart_title field in Insights Dashboard Item if chart is set
    # set as title of Insights Query Chart with name = chart
    frappe.db.sql(
        """
        UPDATE `tabInsights Dashboard Item`
        SET chart_title = (
            SELECT title
            FROM `tabInsights Query Chart`
            WHERE name = chart
        )
        WHERE item_type = 'Chart'
        AND chart IS NOT NULL
        AND chart != ''
    """
    )
