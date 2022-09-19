# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import math
from json import dumps


def execute():
    DASHBOARD_ITEM = "Insights Dashboard Item"
    layouts = frappe.get_all(DASHBOARD_ITEM, fields=["name", "layout"])

    for row in layouts:
        if row.layout:
            layout = frappe.parse_json(row.layout)
            if not layout.width and not layout.height:
                continue

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
