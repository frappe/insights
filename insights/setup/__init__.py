# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
import os

import frappe


def after_install():
    sync_site_tables()


def sync_site_tables():
    if frappe.flags.in_test or os.environ.get("CI"):
        return

    if not frappe.db.exists("Insights Data Source", "Site DB"):
        create_site_db_data_source()

    doc = frappe.get_doc("Insights Data Source", "Site DB")
    doc.enqueue_sync_tables()


def create_site_db_data_source():
    data_source_fixture_path = frappe.get_app_path(
        "insights", "fixtures", "insights_data_source.json"
    )
    with open(data_source_fixture_path, "r") as f:
        site_db = json.load(f)[0]
        frappe.get_doc(site_db).insert()
