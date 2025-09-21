# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import chardet
import frappe


def get_frontend_file(file_path):
    frontend_path = frappe.get_app_path("insights", "../frontend")
    with open(frontend_path + file_path, "rb") as f:
        data = f.read()
        encoding = chardet.detect(data)["encoding"]
        return data.decode(encoding)


def guess_layout_for_chart(chart_type, dashboard):
    file = get_frontend_file("/src/widgets/widgetDimensions.json")
    dimensions = frappe.parse_json(file)
    layout = {"x": 0, "y": 0}
    if chart_type in dimensions:
        layout["w"] = dimensions[chart_type]["defaultWidth"]
        layout["h"] = dimensions[chart_type]["defaultHeight"]
    else:
        layout["w"] = 4
        layout["h"] = 4

    max_y = 0
    for item in dashboard.items:
        item_layout = frappe.parse_json(item.layout)
        max_y = max(max_y, item_layout["y"] + item_layout["h"])
    layout["y"] = max_y
    return layout
