# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
import os
import time

import click
import frappe

from .demo import DemoDataFactory


def after_install():
    import_demo_data()
    import_demo_queries_and_dashboards()
    sync_site_tables()


def import_demo_data():
    try:
        click.secho("Creating demo data...", fg="green")
        start = time.monotonic()
        DemoDataFactory().run()
        click.secho(
            f"Created demo data in {time.monotonic() - start} seconds", fg="green"
        )
    except Exception as e:
        frappe.log_error("Failed to create Demo Data")
        click.secho(f"Error while creating demo data: {e}", fg="red")


def import_demo_queries_and_dashboards():
    try:
        current_path = frappe.get_app_path("insights", "setup")
        with open(current_path + "/demo_queries.json", "r") as f:
            queries = json.load(f)

        for query in queries:
            query_doc = frappe.new_doc("Insights Query")
            query_doc.update(query)
            query_doc.save()

        with open(current_path + "/demo_dashboards.json", "r") as f:
            dashboards = json.load(f)

        for dashboard in dashboards:
            dashboard_doc = frappe.new_doc("Insights Dashboard")
            dashboard_doc.update(dashboard)
            dashboard_doc.save()
    except Exception as e:
        frappe.log_error("Failed to create Demo Queries and Dashboards")
        click.secho(f"Error while creating demo queries and dashboards: {e}", fg="red")


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
