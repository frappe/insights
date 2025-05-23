# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import shutil
from contextlib import contextmanager

import frappe

from insights.api.data_sources import get_data_source_tables
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.insights.doctype.insights_table_link_v3.insights_table_link_v3 import (
    InsightsTableLinkv3,
)
from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook


def update_progress(message, progress):
    print(message, progress)
    frappe.publish_realtime(
        event="insights_demo_setup_progress",
        user=frappe.session.user,
        message={
            "message": message,
            "progress": progress,
            "user": frappe.session.user,
        },
    )


class DemoDataFactory:
    @staticmethod
    def run(force=False):
        with db_connections():
            factory = DemoDataFactory()
            factory.initialize()
            if factory.demo_data_exists() and not force:
                update_progress("Done", 99)
                return factory
            update_progress("Downloading data...", 5)
            factory.download_demo_data()
            update_progress("Syncing tables...", 60)
            factory.sync_tables()
            update_progress("Done", 99)
            factory.create_sample_workbook()
            return factory

    def initialize(self):
        self.db_url = "https://drive.google.com/uc?export=download&id=1l43RqU0KWKr04fx54PLsrHpWqMijRKTa"
        self.files_folder = frappe.get_site_path("private", "files")
        self.db_filename = "insights_demo_data.duckdb"
        self.db_file_path = os.path.join(self.files_folder, self.db_filename)

        self.setup_demo_data_source()
        if frappe.flags.in_test or os.environ.get("CI"):
            test_db_path = os.path.join(os.path.dirname(__file__), self.db_filename)
            shutil.copyfile(test_db_path, self.db_file_path)

    def setup_demo_data_source(self):
        if not frappe.db.exists("Insights Data Source v3", "demo_data"):
            data_source = frappe.new_doc("Insights Data Source v3")
            data_source.name = "demo_data"
            data_source.title = "Demo Data"
            data_source.status = "Active"
            data_source.database_type = "DuckDB"
            data_source.database_name = "insights_demo_data"
            data_source.flags.ignore_permissions = True
            data_source.db_insert()

        self.data_source = frappe.get_doc("Insights Data Source v3", "demo_data")

    def demo_data_exists(self):
        tables = get_data_source_tables(self.data_source.name)
        tables_exists = len(tables) == 8

        links_count = frappe.db.count("Insights Table Link v3", {"data_source": self.data_source.name})
        links_exists = links_count == 8

        sample_workbook_exists = frappe.db.exists("Insights Workbook", {"title": "Order Analysis"})

        return tables_exists and links_exists and sample_workbook_exists

    def download_demo_data(self):
        if frappe.flags.in_test or os.environ.get("CI"):
            return

        import requests

        try:
            with requests.get(self.db_url, stream=True) as r:
                r.raise_for_status()
                with open(self.db_file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            frappe.log_error("Error downloading demo data. Please check your Internet connection.")
            update_progress("Error...", -1)
            raise e

    def sync_tables(self):
        self.data_source.update_table_list()
        self.data_source.save(ignore_permissions=True)
        self.create_table_links()

    def create_table_links(self):
        table_links = [
            {
                "left_table": "customers",
                "right_table": "orders",
                "left_column": "customer_id",
                "right_column": "customer_id",
            },
            {
                "left_table": "geolocation",
                "right_table": "customers",
                "left_column": "geolocation_zip_code_prefix",
                "right_column": "customer_zip_code_prefix",
            },
            {
                "left_table": "geolocation",
                "right_table": "sellers",
                "left_column": "geolocation_zip_code_prefix",
                "right_column": "seller_zip_code_prefix",
            },
            {
                "left_table": "orders",
                "right_table": "orderitems",
                "left_column": "order_id",
                "right_column": "order_id",
            },
            {
                "left_table": "orders",
                "right_table": "orderpayments",
                "left_column": "order_id",
                "right_column": "order_id",
            },
            {
                "left_table": "orders",
                "right_table": "orderreviews",
                "left_column": "order_id",
                "right_column": "order_id",
            },
            {
                "left_table": "products",
                "right_table": "orderitems",
                "left_column": "product_id",
                "right_column": "product_id",
            },
            {
                "left_table": "sellers",
                "right_table": "orderitems",
                "left_column": "seller_id",
                "right_column": "seller_id",
            },
        ]
        frappe.db.delete("Insights Table Link v3", {"data_source": self.data_source.name})
        for link in table_links:
            InsightsTableLinkv3.create(
                self.data_source.name,
                link["left_table"],
                link["right_table"],
                link["left_column"],
                link["right_column"],
            )

    def create_sample_workbook(self):
        if frappe.db.exists("Insights Workbook", {"title": "Order Analysis"}):
            return

        fixture_path = frappe.get_app_path("insights", "setup")
        with open(fixture_path + "/sample_workbook.json") as f:
            sample_workbook = f.read()

        with admin_session():
            import_workbook(frappe.parse_json(sample_workbook))


@contextmanager
def admin_session():
    current_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        yield
    finally:
        frappe.set_user(current_user)
