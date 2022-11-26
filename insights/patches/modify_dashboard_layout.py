# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import math
from json import dumps

import frappe


def execute():
    DASHBOARD_ITEM = "Insights Dashboard Item"
    layouts = frappe.get_all(DASHBOARD_ITEM, fields=["name", "layout"])

    for row in layouts:
        layout = frappe.parse_json(row.layout or {})
        new_layout = dumps({"w": 4, "h": 4}, indent=2)
        if layout.width or layout.height:
            new_layout = update_width_height(layout)

        frappe.db.set_value(
            DASHBOARD_ITEM,
            row.name,
            "layout",
            new_layout,
            update_modified=False,
        )


def update_width_height(layout):
    COL_WIDTH = 55
    ROW_HEIGHT = 30
    if layout.width:
        layout.w = math.ceil(int(layout.width) / COL_WIDTH)
        del layout["width"]
    if layout.height:
        layout.h = math.ceil(int(layout.height) / ROW_HEIGHT)
        del layout["height"]
    return dumps(layout, indent=2)
