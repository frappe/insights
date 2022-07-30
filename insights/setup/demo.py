# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import csv
import frappe


DATA_URL = "https://drive.google.com/u/0/uc?id=1pPWaZ7pz-9ecFjbpjKvYxR1f7VDoJmYU&export=download"
TAR_FILE = "insights_demo_data.tar"
FOLDER_NAME = "insights_demo_data"
PRIVATE_FILES_PATH = None
META = None


def setup_demo():
    global PRIVATE_FILES_PATH
    PRIVATE_FILES_PATH = frappe.get_site_path("private", "files")

    download_demo_data()
    extract_demo_data()
    get_meta()
    create_tables()
    import_csv()
    create_indexes()
    create_data_source()
    hide_other_tables()
    remove_demo_data()


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
        raise e


def extract_demo_data():
    import tarfile

    try:
        with tarfile.open(os.path.join(PRIVATE_FILES_PATH, TAR_FILE)) as tar:
            tar.extractall(PRIVATE_FILES_PATH)
            tar.close()

    except Exception as e:
        frappe.log_error(
            "Error restoring demo data. Please check if the file exists and is not corrupted."
        )
        raise e


def get_meta():
    global META
    if META:
        return
    META = {
        "Current Department Employee": {
            "columns": {
                "Employee ID": "varchar(255)",
                "Department ID": "varchar(255)",
                "From Date": "date",
                "To Date": "date",
            }
        },
        "Employee": {
            "columns": {
                "Employee ID": "varchar(255)",
                "Birth Date": "date",
                "First Name": "varchar(255)",
                "Last Name": "varchar(255)",
                "Gender": "varchar(5)",
                "Hire Date": "date",
            },
        },
        "Department": {
            "columns": {
                "Department ID": "varchar(255)",
                "Department Name": "varchar(255)",
            },
        },
        "Salary": {
            "columns": {
                "Employee ID": "varchar(255)",
                "Salary": "int",
                "From Date": "date",
                "To Date": "date",
            }
        },
        "Department Employee": {
            "columns": {
                "Employee ID": "varchar(255)",
                "Department ID": "varchar(255)",
                "From Date": "date",
                "To Date": "date",
            }
        },
        "Department Employee Latest Date": {
            "columns": {
                "Employee ID": "varchar(255)",
                "From Date": "date",
                "To Date": "date",
            }
        },
        "Department Manager": {
            "columns": {
                "Employee ID": "varchar(255)",
                "Department ID": "varchar(255)",
                "From Date": "date",
                "To Date": "date",
            }
        },
        "Title": {
            "columns": {
                "Employee ID": "varchar(255)",
                "Title": "varchar(255)",
                "From Date": "date",
                "To Date": "date",
            }
        },
    }


def create_tables():
    for table in META.keys():
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


def get_csv_files():
    # get all .csv files from downloaded folder
    folder_path = os.path.join(PRIVATE_FILES_PATH, FOLDER_NAME)
    return [
        f"{os.path.join(folder_path, f)}"
        for f in os.listdir(folder_path)
        if f.endswith(".csv")
    ]


def import_csv():
    csv_files = get_csv_files()
    for csv_file in csv_files:
        table = csv_file.split("/")[-1].split(".")[0]
        columns = META.get(table, {}).get("columns", {})

        if not columns:
            continue

        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
            header = [f"`{col}`" for col in columns]
            header.insert(0, "ID")
            rows = list(reader)
            values = [cell for row in rows for cell in row]
            # insert data into table
            frappe.db.sql(
                f"""
                    INSERT INTO `{table}` ({','.join(header)})
                    VALUES {", ".join([f"({','.join(['%s'] * len(header))})" for _ in rows])}
                """,
                values,
            )
            frappe.db.commit()


def create_indexes():
    indexes = {
        "Current Department Employee": ["`Employee ID`", "`Department ID`"],
        "Employee": ["`Employee ID`"],
        "Department": ["`Department ID`"],
        "Salary": ["`Employee ID`"],
        "Department Employee": ["`Employee ID`", "`Department ID`"],
        "Department Employee Latest Date": ["`Employee ID`"],
        "Department Manager": ["`Employee ID`", "`Department ID`"],
        "Title": ["`Employee ID`"],
    }
    for table in indexes.keys():
        scrubbed = frappe.scrub(table)
        frappe.db.sql(
            f"CREATE INDEX `{scrubbed}` ON `{table}` ({','.join(indexes[table])})"
        )


def create_data_source():
    if frappe.db.exists("Data Source", "Demo Data"):
        doc = frappe.get_doc("Data Source", "Demo Data")
        doc.database_name = frappe.conf.db_name
        doc.username = frappe.conf.db_name
        doc.password = frappe.conf.db_password
        doc.save()
        return

    data_source = frappe.get_doc(
        {
            "doctype": "Data Source",
            "title": "Demo Data",
            "database_type": "MariaDB",
            "database_name": frappe.conf.db_name,
            "username": frappe.conf.db_name,
            "password": frappe.conf.db_password,
        }
    )
    data_source.insert()


def hide_other_tables():
    tables = list(META.keys())
    frappe.db.sql(
        f"""
            UPDATE `tabTable`
            SET `hidden` = 1
            WHERE `data_source` = "Demo Data"
                AND `table` NOT IN ({','.join(['%s'] * len(tables))})
        """,
        tables,
    )


def remove_demo_data():
    if os.path.exists(os.path.join(PRIVATE_FILES_PATH, TAR_FILE)):
        os.remove(os.path.join(PRIVATE_FILES_PATH, TAR_FILE))
