# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os

import frappe


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
    def __init__(self) -> None:
        self.initialize()

    @staticmethod
    def run(force=False):
        factory = DemoDataFactory()
        if factory.demo_data_exists() and not force:
            update_progress("Done", 99)
            return factory
        update_progress("Downloading data...", 5)
        factory.download_demo_data()
        update_progress("Extracting data...", 30)
        factory.extract_demo_data()
        update_progress("Syncing tables...", 60)
        factory.sync_tables()
        update_progress("Cleaning up...", 90)
        factory.cleanup()
        update_progress("Done", 99)
        return factory

    def initialize(self):
        self.data_url = "https://drive.google.com/u/0/uc?id=11EpftRVNilAtMVMX9cNFVd1QFmqx7MYF&export=download"
        self.files_folder = frappe.get_site_path("private", "files")
        self.tar_filename = "insights_demo_data.sqlite.tar"
        self.local_filename = os.path.join(self.files_folder, self.tar_filename)
        self.file_schema = self.get_schema()
        self.table_names = [frappe.scrub(table) for table in self.file_schema.keys()]

        self.create_demo_data_source()
        self.data_source = frappe.get_doc("Insights Data Source", "demo_data")
        if frappe.flags.in_test or os.environ.get("CI"):
            self.local_filename = os.path.join(
                os.path.dirname(__file__), "test_sqlite_db.sqlite.tar"
            )

    def create_demo_data_source(self):
        if not frappe.db.exists("Insights Data Source", "demo_data"):
            data_source = frappe.new_doc("Insights Data Source")
            data_source.title = "Demo Data"
            data_source.database_type = "SQLite"
            data_source.database_name = "insights_demo_data"
            data_source.save(ignore_permissions=True)
            frappe.db.commit()

    def demo_data_exists(self):
        if not self.data_source.tables:
            return False
        return len(frappe.parse_json(self.data_source.tables)) == len(self.table_names)

    def get_schema(self):
        return {
            "Customers": {
                "columns": {
                    "customer_id": "String",
                    "customer_unique_id": "String",
                    "customer_zip_code_prefix": "String",
                    "customer_city": "String",
                    "customer_state": "String",
                },
            },
            # "Geolocation": {
            #     "columns": {
            #         "geolocation_zip_code_prefix": "String",
            #         "geolocation_lat": "String",
            #         "geolocation_lng": "String",
            #         "geolocation_city": "String",
            #         "geolocation_state": "String",
            #     }
            # },
            "OrderItems": {
                "columns": {
                    "order_id": "String",
                    "order_item_id": "String",
                    "product_id": "String",
                    "seller_id": "String",
                    "shipping_limit_date": "Datetime",
                    "price": "Decimal",
                    "freight_value": "Decimal",
                }
            },
            "OrderPayments": {
                "columns": {
                    "order_id": "String",
                    "payment_sequential": "String",
                    "payment_type": "String",
                    "payment_installments": "Integer",
                    "payment_value": "Decimal",
                }
            },
            "OrderReviews": {
                "columns": {
                    "review_id": "String",
                    "order_id": "String",
                    "review_score": "Integer",
                    "review_comment_title": "String",
                    "review_comment_message": "Text",
                    "review_creation_date": "Datetime",
                    "review_answer_timestamp": "Datetime",
                }
            },
            "Orders": {
                "columns": {
                    "order_id": "String",
                    "customer_id": "String",
                    "order_status": "String",
                    "order_purchase_timestamp": "Datetime",
                    "order_approved_at": "Datetime",
                    "order_delivered_carrier_date": "Datetime",
                    "order_delivered_customer_date": "Datetime",
                    "order_estimated_delivery_date": "Datetime",
                }
            },
            "Products": {
                "columns": {
                    "product_id": "String",
                    "product_category_name": "String",
                    "product_weight_g": "Integer",
                    "product_length_cm": "Integer",
                    "product_height_cm": "Integer",
                    "product_width_cm": "Integer",
                }
            },
            "Sellers": {
                "columns": {
                    "seller_id": "String",
                    "seller_zip_code_prefix": "String",
                    "seller_city": "String",
                    "seller_state": "String",
                }
            },
        }

    def cleanup(self):
        if os.path.exists(os.path.join(self.files_folder, self.tar_filename)):
            os.remove(os.path.join(self.files_folder, self.tar_filename))

    def download_demo_data(self):
        """Download file locally under sites path and return local path"""
        if os.path.exists(self.local_filename):
            return

        import requests

        try:
            with requests.get(self.data_url, stream=True) as r:
                r.raise_for_status()
                with open(self.local_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            frappe.log_error(
                "Error downloading demo data. Please check your Internet connection."
            )
            update_progress("Error...", -1)
            raise e

    def extract_demo_data(self):
        import tarfile

        try:
            with tarfile.open(self.local_filename) as tar:
                tar.extractall(self.files_folder)
                tar.close()
        except Exception as e:
            frappe.log_error(
                "Error extracting demo data. Please check if the file exists and is not corrupted."
            )
            update_progress("Error...", -1)
            raise e

    def sync_tables(self):
        self.data_source.update_table_list()
        self.data_source.save(ignore_permissions=True)

    def create_table_links(self):
        # TODO: refactor table links, create a new table for table links
        foreign_key_relations = {
            "Customers": [["customer_id", "Orders", "customer_id"]],
            # "Geolocation": [
            #     [
            #         "geolocation_zip_code_prefix",
            #         "Customers",
            #         "customer_zip_code_prefix",
            #     ],
            #     [
            #         "geolocation_zip_code_prefix",
            #         "Suppliers",
            #         "supplier_zip_code_prefix",
            #     ],
            # ],
            "Orders": [
                ["order_id", "OrderItems", "order_id"],
                ["order_id", "OrderPayments", "order_id"],
                ["order_id", "OrderReviews", "order_id"],
            ],
            "Products": [
                ["product_id", "OrderItems", "product_id"],
            ],
            "Sellers": [
                ["seller_id", "OrderItems", "seller_id"],
            ],
        }
        for table, links in foreign_key_relations.items():
            doc = frappe.get_doc(
                "Insights Table",
                {"table": frappe.scrub(table), "data_source": self.data_source.name},
            )
            for link in links:
                doc.append(
                    "table_links",
                    {
                        "primary_key": link[0],
                        "foreign_key": link[2],
                        "foreign_table": frappe.scrub(link[1]),
                        "foreign_table_label": link[1],
                        "cardinality": "1:N",
                    },
                )
            doc.save(ignore_permissions=True)
