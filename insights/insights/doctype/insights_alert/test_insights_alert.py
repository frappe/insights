# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from insights.http import OutboundRequestRefused
from insights.insights.doctype.insights_alert.insights_alert import (
    WEBHOOK_MAX_ROWS,
    InsightsAlert,
    send_alerts,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
)

POST = "insights.insights.doctype.insights_alert.insights_alert.post_to_public_url"


def message_context(row_count=1):
    return {
        "alert": {"title": "Late invoices"},
        "query": {"title": "Invoices overdue"},
        "count": row_count,
        "rows": [{"invoice": f"INV-{i}"} for i in range(row_count)],
    }


def webhook_alert():
    """An unsaved alert, which is all `send_webhook_alert` reads."""
    doc = frappe.new_doc("Insights Alert")
    doc.title = "Late invoices"
    doc.channel = "Webhook"
    doc.webhook_url = "https://example.com/hooks/insights"
    doc.webhook_token = "sekret-token"
    return doc


class TestWebhookPayload(IntegrationTestCase):
    """The payload is a contract with a receiver's parser. Pin its shape."""

    def post_one(self, context):
        with patch(POST) as post:
            webhook_alert().send_webhook_alert("**3 invoices are overdue**", context)
        return frappe.parse_json(post.call_args.kwargs["data"]), post.call_args

    def test_payload_carries_a_version(self):
        payload, _ = self.post_one(message_context())
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["event"], "insights_alert")
        self.assertEqual(payload["message"], "**3 invoices are overdue**")
        self.assertEqual(payload["context"]["alert"], "Late invoices")
        self.assertEqual(payload["context"]["query"], "Invoices overdue")

    def test_token_travels_in_the_authorization_header(self):
        """Not in the URI, which would land it in the receiver's access logs."""
        _, call = self.post_one(message_context())
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer sekret-token")
        self.assertNotIn("sekret-token", call.args[0])

    def test_rows_are_capped_and_the_cap_is_declared(self):
        payload, _ = self.post_one(message_context(row_count=WEBHOOK_MAX_ROWS + 150))
        self.assertEqual(len(payload["context"]["rows"]), WEBHOOK_MAX_ROWS)
        self.assertEqual(payload["context"]["count"], WEBHOOK_MAX_ROWS + 150)
        self.assertTrue(payload["context"]["truncated"])

    def test_a_short_result_is_not_marked_truncated(self):
        payload, _ = self.post_one(message_context(row_count=3))
        self.assertEqual(len(payload["context"]["rows"]), 3)
        self.assertFalse(payload["context"]["truncated"])


class TestWebhookFailures(IntegrationTestCase):
    def test_a_status_code_is_reported(self):
        response = requests.Response()
        response.status_code = 503
        error = requests.HTTPError(response=response)
        with patch(POST, side_effect=error):
            with self.assertRaisesRegex(frappe.ValidationError, "returned 503"):
                webhook_alert().send_webhook_alert("msg", message_context())

    def test_transport_failure_does_not_leak_the_exception_text(self):
        """Any Insights User can reach this. It gets the class, not the internals."""
        with patch(POST, side_effect=requests.ConnectionError("connect to 10.1.2.3 failed")):
            with self.assertRaises(frappe.ValidationError) as raised:
                webhook_alert().send_webhook_alert("msg", message_context())
        self.assertNotIn("10.1.2.3", str(raised.exception))
        self.assertIn("ConnectionError", str(raised.exception))

    def test_a_refusal_is_passed_through_unchanged(self):
        """It already says what it refused, so restating it loses the reason."""
        refusal = OutboundRequestRefused("resolves to a non-public address (10.0.0.1)")
        with patch(POST, side_effect=refusal):
            with self.assertRaisesRegex(OutboundRequestRefused, "non-public address"):
                webhook_alert().send_webhook_alert("msg", message_context())


class TestFailedAlertIsNotRetriedEveryTick(InsightsIntegrationTestCase):
    # `send_alerts` rolls back what it catches, which would take the fixtures
    # with it. Committing them in class setup is what keeps them around.

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook("Administrator")
        query = create_test_query("Administrator", cls.workbook.name)
        cls.alert = frappe.get_doc(
            doctype="Insights Alert",
            title="Webhook that is down",
            channel="Webhook",
            query=query.name,
            frequency="Daily",
            condition="q['status'] == 'Open'",
            custom_condition=1,
            message="{{ rows }}",
            webhook_url="https://example.com/hooks/insights",
            webhook_token="sekret-token",
        ).insert()

    @classmethod
    def after_class(cls):
        frappe.delete_doc("Insights Alert", cls.alert.name, force=True)
        frappe.delete_doc("Insights Workbook", cls.workbook.name, force=True)

    def test_a_failed_delivery_records_the_run(self):
        """`last_execution` is the cron's start point. Left unset by a failure,
        the alert is due again on the next four-minute tick and a dead endpoint
        gets several hundred POSTs a day.

        The condition is stubbed to met: this is about what the scheduler
        records, not about what the query returns.
        """
        self.assertIsNone(self.alert.last_execution)

        with (
            patch.object(InsightsAlert, "evaluate_condition", return_value=True),
            patch.object(InsightsAlert, "get_message_context", return_value=message_context()),
            patch(POST, side_effect=requests.ConnectionError("endpoint is down")),
        ):
            send_alerts()

        self.assertIsNotNone(frappe.db.get_value("Insights Alert", self.alert.name, "last_execution"))


class TestEmailRecipients(InsightsIntegrationTestCase):
    """An email alert carries its query's rows, so it may only reach this site."""

    MEMBER = "alert_recipient@test.com"
    OUTSIDER = "someone@external.example.org"

    @classmethod
    def before_class(cls):
        create_user(cls.MEMBER, first_name="Alert", last_name="Recipient", roles="Insights User")
        cls.workbook = create_test_workbook("Administrator", title="Alert Workbook").name
        cls.query = create_test_query("Administrator", cls.workbook, title="Alert Query").name

    @classmethod
    def after_class(cls):
        frappe.delete_doc("Insights Workbook", cls.workbook, force=True)
        delete_users(cls.MEMBER)

    def email_alert(self, recipients):
        doc = frappe.new_doc("Insights Alert")
        doc.title = "Overdue invoices"
        doc.channel = "Email"
        doc.query = self.query
        doc.frequency = "Daily"
        doc.custom_condition = 1
        doc.condition = "q['status'] == 'Open'"
        doc.message = "{{ rows }}"
        doc.recipients = recipients
        return doc

    def test_a_user_of_this_site_is_a_recipient(self):
        self.assertEqual(self.email_alert(self.MEMBER).get_recipients(), [self.MEMBER])

    def test_an_address_outside_this_site_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.email_alert(self.OUTSIDER).get_recipients()

    def test_one_outside_address_refuses_the_whole_list(self):
        with self.assertRaises(frappe.ValidationError):
            self.email_alert(f"{self.MEMBER},{self.OUTSIDER}").get_recipients()

    def test_a_disabled_user_is_refused(self):
        frappe.db.set_value("User", self.MEMBER, "enabled", 0)
        self.addCleanup(frappe.db.set_value, "User", self.MEMBER, "enabled", 1)
        with self.assertRaises(frappe.ValidationError):
            self.email_alert(self.MEMBER).get_recipients()

    def test_saving_the_alert_applies_the_same_bound(self):
        with (
            patch.object(InsightsAlert, "evaluate_condition", return_value=True),
            self.assertRaises(frappe.ValidationError),
        ):
            self.email_alert(self.OUTSIDER).insert()
