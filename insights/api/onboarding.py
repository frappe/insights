# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def is_onboarded():
    return bool(frappe.get_single("Insights Settings").setup_complete)


def get_new_datasource(db):
    data_source = frappe.new_doc("Data Source")
    data_source.update(
        {
            "database_type": db.get("type"),
            "database_name": db.get("name"),
            "title": db.get("title"),
            "host": db.get("host"),
            "port": db.get("port"),
            "username": db.get("username"),
            "password": db.get("password"),
            "use_ssl": db.get("useSSL"),
        }
    )
    return data_source


@frappe.whitelist()
def test_database_connection(db):
    data_source = get_new_datasource(db)
    return data_source.test_connection()


@frappe.whitelist()
def add_database(db):
    data_source = get_new_datasource(db)
    data_source.save()
    update_onboarding_status()


def update_onboarding_status():
    settings = frappe.get_single("Insights Settings")
    settings.setup_complete = 1
    settings.save()


@frappe.whitelist()
def setup_demo():
    from insights.setup.demo import setup_db

    setup_db()
    update_onboarding_status()
