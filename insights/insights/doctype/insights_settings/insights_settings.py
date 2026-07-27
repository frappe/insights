# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# Interactive queries block a web worker and hold a connection on the source DB,
# so the cap is tuned for a viewer waiting on a dashboard, not for long analytics.
# Background imports bypass this (see _disable_statement_timeout).
DEFAULT_MAX_EXECUTION_TIME = 60


def get_max_execution_time() -> int:
    return frappe.db.get_single_value("Insights Settings", "max_execution_time", cache=True) or (
        DEFAULT_MAX_EXECUTION_TIME
    )


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

    @frappe.whitelist()
    def update_settings(self, settings: dict | str):
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
