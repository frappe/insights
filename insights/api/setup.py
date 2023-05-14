# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights.api.telemetry import track
from insights.setup.demo import setup


@frappe.whitelist()
def setup_complete():
    return bool(frappe.get_single("Insights Settings").setup_complete)


def get_new_datasource(db):
    data_source = frappe.new_doc("Insights Data Source")
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
    return data_source.test_connection(raise_exception=True)


@frappe.whitelist()
def add_database(db):
    track("add_data_source")
    data_source = get_new_datasource(db)
    data_source.save()
    data_source.enqueue_sync_tables()
    update_setup_status()


def update_setup_status():
    settings = frappe.get_single("Insights Settings")
    settings.setup_complete = 1
    settings.save()


@frappe.whitelist()
def setup_demo():
    from frappe.utils.scheduler import is_scheduler_inactive

    if is_scheduler_inactive():
        frappe.errprint("Scheduler is inactive")
        _setup_demo()
        return

    frappe.enqueue(_setup_demo, job_name="insights_demo_setup", now=False)


def _setup_demo():
    setup()
    update_setup_status()
    frappe.publish_realtime(
        event="insights_demo_setup_progress",
        message={
            "progress": 100,
            "message": "Done",
            "user": frappe.session.user,
        },
    )
