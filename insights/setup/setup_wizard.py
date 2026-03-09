# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import os

import frappe

from insights.decorators import insights_whitelist
from insights.setup.demo import DemoDataFactory


@insights_whitelist(role="Insights Admin")
def check_demo_data_exists() -> bool:
    from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
        db_connections,
    )

    if not frappe.db.exists("Insights Data Source v3", "demo_data"):
        return False

    with db_connections():
        factory = DemoDataFactory()
        factory.initialize()
        return factory.demo_data_exists()


@insights_whitelist(role="Insights Admin")
def setup_demo_data():
    if frappe.flags.in_test or os.environ.get("CI"):
        return

    try:
        factory = DemoDataFactory()
        factory.run()
        frappe.db.commit()
    except Exception:
        frappe.log_error("Insights: Demo Data Setup Failed")
        frappe.throw("Failed to setup demo data")
