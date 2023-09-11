# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def guess_layout_for_chart(chart_type, dashboard):
    # guess the width and height of the chart
    layout = {"w": 16, "h": 10, "x": 0, "y": 0}
    if chart_type == "Number":
        layout["w"] = 4
        layout["h"] = 3
    if chart_type == "Progress":
        layout["w"] = 4
        layout["h"] = 4

    max_y = 0
    for item in dashboard.items:
        item_layout = frappe.parse_json(item.layout)
        max_y = max(max_y, item_layout["y"] + item_layout["h"])
    layout["y"] = max_y
    return layout
