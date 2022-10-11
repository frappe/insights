# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import csv
import frappe


DATA_URL = "https://drive.google.com/u/1/uc?id=1OyqgwpqaxFY9lLnFpk2pZmihQng0ipk6&export=download"
TAR_FILE = "insights_demo_data.tar"
FOLDER_NAME = "insights_demo_data"
PRIVATE_FILES_PATH = None
META = None


def setup():
    initialize_demo_setup()

    if demo_data_exists():
        update_progress("Done", 99)
        return

    update_progress("Downloading data...", 5)
    download_demo_data()

    update_progress("Extracting data...", 15)
    extract_demo_data()

    update_progress("Inserting a lot of entries...", 30)
    create_tables()
    import_csv()

    update_progress("Optimizing reads...", 75)
    create_indexes()

    update_progress("Building relations...", 80)
    create_data_source()
    create_table_links()

    update_progress("Cleaning up...", 90)
    hide_other_tables()
    remove_demo_data()

    update_progress("Done", 99)


def update_progress(message, progress):
    frappe.publish_realtime(
        event="insights_demo_setup_progress",
        message={
            "message": message,
            "progress": progress,
            "user": frappe.session.user,
        },
    )


def demo_data_exists():
    tables = list(META.keys())
    res = frappe.db.sql(
        f"""
            SELECT name
            FROM `tabInsights Table`
            WHERE `data_source` = "Demo Data"
                AND `table` IN ({','.join(['%s'] * len(tables))})
        """,
        tables,
    )
    return len(res) == len(tables)


def initialize_demo_setup():
    global META
    META = get_schema()

    global PRIVATE_FILES_PATH
    PRIVATE_FILES_PATH = frappe.get_site_path("private", "files")


def download_demo_data():
    import requests

    """Download file locally under sites path and return local path"""
    local_filename = os.path.join(PRIVATE_FILES_PATH, TAR_FILE)
    try:
        with requests.get(DATA_URL, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        frappe.log_error(
            "Error downloading demo data. Please check your internet connection."
        )
        update_progress("Error...", -1)
        raise e


def extract_demo_data():
    import tarfile

    try:
        with tarfile.open(os.path.join(PRIVATE_FILES_PATH, TAR_FILE)) as tar:
            tar.extractall(PRIVATE_FILES_PATH)
            tar.close()

    except Exception as e:
        frappe.log_error(
            "Error extracting demo data. Please check if the file exists and is not corrupted."
        )
        update_progress("Error...", -1)
        raise e


def get_schema():
    return {
        "Customers": {
            "columns": {
                "customer_id": "varchar(255)",
                "customer_unique_id": "varchar(255)",
                "customer_zip_code_prefix": "varchar(255)",
                "customer_city": "varchar(255)",
                "customer_state": "varchar(255)",
            }
        },
        "Geolocation": {
            "columns": {
                "geolocation_zip_code_prefix": "varchar(255)",
                "geolocation_lat": "varchar(255)",
                "geolocation_lng": "varchar(255)",
                "geolocation_city": "varchar(255)",
                "geolocation_state": "varchar(255)",
            }
        },
        "OrderItems": {
            "columns": {
                "order_id": "varchar(255)",
                "order_item_id": "varchar(255)",
                "product_id": "varchar(255)",
                "seller_id": "varchar(255)",
                "shipping_limit_date": "datetime",
                "price": "decimal",
                "freight_value": "decimal",
            }
        },
        "OrderPayments": {
            "columns": {
                "order_id": "varchar(255)",
                "payment_sequential": "varchar(255)",
                "payment_type": "varchar(255)",
                "payment_installments": "int",
                "payment_value": "decimal",
            }
        },
        "OrderReviews": {
            "columns": {
                "review_id": "varchar(255)",
                "order_id": "varchar(255)",
                "review_score": "int",
                "review_comment_title": "varchar(255)",
                "review_comment_message": "text",
                "review_creation_date": "datetime",
                "review_answer_timestamp": "datetime",
            }
        },
        "Orders": {
            "columns": {
                "order_id": "varchar(255)",
                "customer_id": "varchar(255)",
                "order_status": "varchar(255)",
                "order_purchase_timestamp": "datetime",
                "order_approved_at": "datetime",
                "order_delivered_carrier_date": "datetime",
                "order_delivered_customer_date": "datetime",
                "order_estimated_delivery_date": "datetime",
            }
        },
        "Products": {
            "columns": {
                "product_id": "varchar(255)",
                "product_category_name": "varchar(255)",
                "product_weight_g": "int",
                "product_length_cm": "int",
                "product_height_cm": "int",
                "product_width_cm": "int",
            }
        },
        "Sellers": {
            "columns": {
                "seller_id": "varchar(255)",
                "seller_zip_code_prefix": "varchar(255)",
                "seller_city": "varchar(255)",
                "seller_state": "varchar(255)",
            }
        },
    }


def create_entries():
    create_tables()
    import_csv()


def create_tables():
    start_progress = 30
    end_progress = 40
    frappe.db.commit()
    for idx, table in enumerate(META.keys()):
        columns = META[table]["columns"]
        # create a table
        frappe.db.sql("DROP TABLE IF EXISTS `{}`".format(table))
        frappe.db.sql(
            f"""CREATE TABLE `{table}` (
                `ID` INT(11) NOT NULL AUTO_INCREMENT,
                {','.join([f"`{col}` {columns[col]}" for col in columns.keys()])},
                PRIMARY KEY (`ID`)
            )"""
        )
        update_progress(
            "Inserting a lot of entries...",
            start_progress + (idx * (end_progress - start_progress)) / len(META.keys()),
        )


def get_csv_files():
    # get all .csv files from downloaded folder
    folder_path = os.path.join(PRIVATE_FILES_PATH, FOLDER_NAME)
    return [
        f"{os.path.join(folder_path, f)}"
        for f in os.listdir(folder_path)
        if f.endswith(".csv")
    ]


def import_csv():
    start_progress = 40
    end_progress = 75
    files = get_csv_files()
    for idx, file in enumerate(files):
        table = file.split("/")[-1].split(".")[0]
        columns = META.get(table, {}).get("columns", {})

        if not columns:
            continue

        with open(file, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
            header = [f"`{col}`" for col in columns]
            # header.insert(0, "`ID`")
            rows = list(reader)
            # batch process rows in batches of 10000
            for i in range(0, len(rows), 10000):
                _rows = rows[i : i + 10000]
                values = [cell or None for row in _rows for cell in row]
                # insert data into table
                frappe.db.sql(
                    f"""
                        INSERT INTO `{table}` ({','.join(header)})
                        VALUES {", ".join([f"({','.join(['%s'] * len(header))})" for _ in _rows])}
                    """,
                    values,
                )
                frappe.db.commit()
                update_progress(
                    "Inserting a lot of entries...",
                    start_progress
                    + (idx * (end_progress - start_progress)) / len(files),
                )


def create_indexes():
    indexes = {
        "Customers": ["customer_id"],
        "Geolocation": ["geolocation_zip_code_prefix"],
        "OrderItems": ["order_id", "product_id", "seller_id"],
        "OrderPayments": ["order_id"],
        "OrderReviews": ["review_id", "order_id"],
        "Orders": ["order_id", "customer_id"],
        "Products": ["product_id"],
        "Sellers": ["seller_id"],
    }
    for table in indexes.keys():
        frappe.db.sql(
            f"CREATE INDEX `{table}` ON `{table}` ({','.join(indexes[table])})"
        )


def create_data_source():
    if frappe.db.exists("Insights Data Source", "Demo Data"):
        doc = frappe.get_doc("Insights Data Source", "Demo Data")
        doc.database_name = frappe.conf.db_name
        doc.username = frappe.conf.db_name
        doc.password = frappe.conf.db_password
        doc.save()
        return

    data_source = frappe.new_doc("Insights Data Source")
    data_source.title = "Demo Data"
    data_source.source_type = "Remote Database"  # TODO: change to "Application Database" when create_insights_tables is fixed
    data_source.database_type = "MariaDB"
    data_source.database_name = frappe.conf.db_name
    data_source.username = frappe.conf.db_name
    data_source.password = frappe.conf.db_password
    data_source.status = "Active"
    data_source.insert()
    data_source.connector.create_insights_tables()


def create_table_links():
    foreign_key_relations = {
        "Customers": [
            ["customer_id", "Orders", "customer_id"],
            ["customer_zip_code_prefix", "Geolocation", "geolocation_zip_code_prefix"],
        ],
        "Geolocation": [
            ["geolocation_zip_code_prefix", "Customers", "customer_zip_code_prefix"],
            ["geolocation_zip_code_prefix", "Suppliers", "supplier_zip_code_prefix"],
        ],
        "OrderItems": [
            ["order_id", "Orders", "order_id"],
            ["product_id", "Products", "product_id"],
            ["seller_id", "Sellers", "seller_id"],
        ],
        "OrderPayments": [
            ["order_id", "Orders", "order_id"],
        ],
        "OrderReviews": [
            ["order_id", "Orders", "order_id"],
        ],
        "Orders": [
            ["customer_id", "Customers", "customer_id"],
            ["order_id", "OrderItems", "order_id"],
            ["order_id", "OrderPayments", "order_id"],
            ["order_id", "OrderReviews", "order_id"],
        ],
        "Products": [
            ["product_id", "OrderItems", "product_id"],
        ],
        "Sellers": [
            ["seller_zip_code_prefix", "Geolocation", "geolocation_zip_code_prefix"],
            ["seller_id", "OrderItems", "seller_id"],
        ],
    }
    for table, links in foreign_key_relations.items():
        doc = frappe.get_doc(
            "Insights Table", {"table": table, "data_source": "Demo Data"}
        )
        for link in links:
            doc.append(
                "table_links",
                {
                    "primary_key": link[0],
                    "foreign_key": link[2],
                    "foreign_table": link[1],
                    "foreign_table_label": link[1],
                },
            )
        doc.save()


def cleanup():
    hide_other_tables()
    remove_demo_data()


def hide_other_tables():
    tables = list(META.keys())
    frappe.db.sql(
        f"""
            UPDATE `tabInsights Table`
            SET `hidden` = 1
            WHERE `data_source` = "Demo Data"
                AND `table` NOT IN ({','.join(['%s'] * len(tables))})
        """,
        tables,
    )


def remove_demo_data():
    if os.path.exists(os.path.join(PRIVATE_FILES_PATH, TAR_FILE)):
        os.remove(os.path.join(PRIVATE_FILES_PATH, TAR_FILE))
