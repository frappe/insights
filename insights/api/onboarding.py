# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from insights.setup.demo import setup
from frappe.utils.scheduler import is_scheduler_inactive
from frappe.core.page.background_jobs.background_jobs import get_info


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
    if is_scheduler_inactive():
        return

    job_name = "insights_demo_setup"
    if not job_already_enqueued(job_name):
        frappe.enqueue(_setup_demo, job_name=job_name)


def _setup_demo():
    setup()
    update_onboarding_status()
    frappe.publish_realtime(
        event="insights_demo_setup_progress",
        message={
            "progress": 100,
            "message": "Done",
            "user": frappe.session.user,
        },
    )


def job_already_enqueued(job_name):
    enqueued_jobs = [d.get("job_name") for d in get_info()]
    if job_name in enqueued_jobs:
        return True
