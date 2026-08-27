"""A failed connection reports the fact to everyone and the reason to few.

A published query runs against a data source the caller cannot read, so the
driver's exception travels back to whoever asked — including a Guest. That
exception names the host, the account, and for a source configured by
connection string the password with it.
"""

from unittest.mock import patch

import frappe

import insights
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    DataSourceConnectionError,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_user, delete_users

ADMIN = "connection_errors_admin@test.com"
USER = "connection_errors_user@test.com"

SECRET = "hunter2"
DRIVER_ERROR = OSError(f'connection to "postgresql://svc:{SECRET}@warehouse.internal" failed')


class TestConnectionErrorReporting(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_user(ADMIN, first_name="Connection", last_name="Admin", roles="Insights Admin")
        create_user(USER, first_name="Connection", last_name="User", roles="Insights User")
        cls.data_source = (
            frappe.get_doc(
                {
                    "doctype": DT.DATA_SOURCE,
                    "title": "Unreachable Source",
                    "database_type": "DuckDB",
                    "database_name": "unreachable",
                }
            )
            .insert()
            .name
        )

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.DATA_SOURCE, cls.data_source, force=True, ignore_permissions=True)
        delete_users(ADMIN, USER)

    def connect_as(self, user):
        """Return the message raised when the driver refuses the connection."""
        # the source connected once on insert, and a live backend short-circuits
        insights.db_connections.pop(self.data_source, None)
        doc = frappe.get_doc(DT.DATA_SOURCE, self.data_source)
        with self.as_user(user), patch.object(doc, "_get_db_connection", side_effect=DRIVER_ERROR):
            with self.assertRaises(DataSourceConnectionError):
                doc._get_ibis_backend()
        return frappe.message_log[-1].get("message")

    def test_an_insights_user_reads_no_driver_detail(self):
        message = self.connect_as(USER)
        self.assertNotIn(SECRET, message)
        self.assertNotIn("warehouse.internal", message)
        self.assertIn("Unreachable Source", message)

    def test_a_guest_reads_no_driver_detail(self):
        message = self.connect_as("Guest")
        self.assertNotIn(SECRET, message)
        self.assertNotIn("warehouse.internal", message)

    def test_whoever_may_edit_the_source_reads_the_driver_detail(self):
        self.assertIn(SECRET, self.connect_as(ADMIN))
