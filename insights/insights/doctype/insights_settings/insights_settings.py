# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import os

import frappe
from frappe.model.document import Document


class InsightsSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        allow_subquery: DF.Check
        allowed_origins: DF.Data | None
        apply_user_permissions: DF.Check
        auto_execute_query: DF.Check
        enable_data_store: DF.Check
        enable_permissions: DF.Check
        fiscal_year_start: DF.Date | None
        max_execution_time: DF.Int
        max_memory_usage: DF.Int
        max_records_to_sync: DF.Int
        onboarding_complete: DF.Check
        query_result_expiry: DF.Int
        query_result_limit: DF.Int
        setup_complete: DF.Check
        telegram_api_token: DF.Password | None
        week_starts_on: DF.Literal[
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ]
    # end: auto-generated types

    def before_save(self):
        if self.setup_complete and not self.get_doc_before_save().setup_complete:
            sync_site_tables()

    @frappe.whitelist()
    def update_settings(self, settings):
        settings = frappe.parse_json(settings)
        if hasattr(settings, "auto_execute_query"):
            self.auto_execute_query = settings.auto_execute_query
        if hasattr(settings, "query_result_expiry"):
            self.query_result_expiry = settings.query_result_expiry
        if hasattr(settings, "query_result_limit"):
            self.query_result_limit = settings.query_result_limit
        if hasattr(settings, "allow_subquery"):
            self.allow_subquery = settings.allow_subquery
        if hasattr(settings, "telegram_api_token"):
            self.telegram_api_token = settings.telegram_api_token
        self.save()

    @property
    def is_subscribed(self):
        try:
            return 1 if frappe.conf.sk_insights else 0
        except Exception:
            return None


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
