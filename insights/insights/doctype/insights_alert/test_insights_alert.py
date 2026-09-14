# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
import requests
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime, validate_email_address

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

    # @feature alerts.webhook
    def test_payload_carries_a_version(self):
        payload, _ = self.post_one(message_context())
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["event"], "insights_alert")
        self.assertEqual(payload["message"], "**3 invoices are overdue**")
        self.assertEqual(payload["context"]["alert"], "Late invoices")
        self.assertEqual(payload["context"]["query"], "Invoices overdue")

    # @feature alerts.webhook
    def test_token_travels_in_the_authorization_header(self):
        """Not in the URI, which would land it in the receiver's access logs."""
        _, call = self.post_one(message_context())
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer sekret-token")
        self.assertNotIn("sekret-token", call.args[0])

    # @feature alerts.webhook
    def test_rows_are_capped_and_the_cap_is_declared(self):
        payload, _ = self.post_one(message_context(row_count=WEBHOOK_MAX_ROWS + 150))
        self.assertEqual(len(payload["context"]["rows"]), WEBHOOK_MAX_ROWS)
        self.assertEqual(payload["context"]["count"], WEBHOOK_MAX_ROWS + 150)
        self.assertTrue(payload["context"]["truncated"])

    # @feature alerts.webhook
    def test_a_short_result_is_not_marked_truncated(self):
        payload, _ = self.post_one(message_context(row_count=3))
        self.assertEqual(len(payload["context"]["rows"]), 3)
        self.assertFalse(payload["context"]["truncated"])


class TestWebhookFailures(IntegrationTestCase):
    # @feature alerts.webhook
    def test_a_status_code_is_reported(self):
        response = requests.Response()
        response.status_code = 503
        error = requests.HTTPError(response=response)
        with patch(POST, side_effect=error):
            with self.assertRaisesRegex(frappe.ValidationError, "returned 503"):
                webhook_alert().send_webhook_alert("msg", message_context())

    # @feature alerts.webhook
    def test_transport_failure_does_not_leak_the_exception_text(self):
        """Any Insights User can reach this. It gets the class, not the internals."""
        with patch(POST, side_effect=requests.ConnectionError("connect to 10.1.2.3 failed")):
            with self.assertRaises(frappe.ValidationError) as raised:
                webhook_alert().send_webhook_alert("msg", message_context())
        self.assertNotIn("10.1.2.3", str(raised.exception))
        self.assertIn("ConnectionError", str(raised.exception))

    # @feature alerts.webhook
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

    # @feature alerts.failed-run-recorded
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
    """A recipient list is read at save, and the mail it produces says who sent it."""

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

    # @feature alerts.email
    def test_an_address_outside_this_site_is_a_recipient(self):
        """A report goes to a client or an accountant as often as to a colleague."""
        self.assertEqual(self.email_alert(self.OUTSIDER).get_recipients(), [self.OUTSIDER])

    # @feature alerts.email
    def test_a_list_is_split_and_trimmed(self):
        alert = self.email_alert(f" {self.MEMBER} , {self.OUTSIDER} ")
        self.assertEqual(alert.get_recipients(), [self.MEMBER, self.OUTSIDER])

    # @feature alerts.email
    def test_an_empty_list_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.email_alert("  ,  ").get_recipients()

    # @feature alerts.email
    def test_saving_reads_the_list(self):
        """`send_alerts` logs a send-time error and marks the alert as run, so a
        list checked only at send fails where nobody is looking."""
        with (
            patch.object(InsightsAlert, "evaluate_condition", return_value=True),
            self.assertRaisesRegex(frappe.ValidationError, "not a valid email address"),
        ):
            self.email_alert("not-an-address").insert()


class TestAlertMailIsAttributable(InsightsIntegrationTestCase):
    """The mail carries the marks that say it is an Insights alert."""

    AUTHOR = "alert_author@test.com"

    @classmethod
    def before_class(cls):
        create_user(cls.AUTHOR, first_name="Alert", last_name="Author", roles="Insights User")
        cls.workbook = create_test_workbook("Administrator", title="Mail Workbook").name
        cls.query = create_test_query("Administrator", cls.workbook, title="Mail Query").name

    @classmethod
    def after_class(cls):
        frappe.delete_doc("Insights Workbook", cls.workbook, force=True)
        delete_users(cls.AUTHOR)

    def alert(self, owner=None):
        doc = frappe.new_doc("Insights Alert")
        doc.title = "Overdue invoices"
        doc.channel = "Email"
        doc.query = self.query
        doc.frequency = "Daily"
        doc.custom_condition = 1
        doc.condition = "q['status'] == 'Open'"
        doc.message = "hello"
        doc.recipients = "someone@external.example.org"
        with patch.object(InsightsAlert, "evaluate_condition", return_value=True):
            doc.insert()
        if owner:
            doc.db_set("owner", owner, update_modified=False)
            doc.owner = owner
        self.addCleanup(frappe.delete_doc, "Insights Alert", doc.name, force=True)
        return doc

    # @feature alerts.email
    def test_a_reply_reaches_the_author(self):
        doc = self.alert(owner=self.AUTHOR)
        with patch("frappe.sendmail") as sendmail:
            doc.send_email_alert("hello")
        self.assertEqual(sendmail.call_args.kwargs["reply_to"], self.AUTHOR)

    # @feature alerts.email
    def test_an_admin_owned_alert_replies_to_an_address(self):
        """`owner` is a User name, and for the admin that name is
        "Administrator". `sendmail` refuses a reply_to it cannot parse."""
        doc = self.alert()
        self.assertEqual(doc.owner, "Administrator")
        with patch("frappe.sendmail") as sendmail:
            doc.send_email_alert("hello")
        reply_to = sendmail.call_args.kwargs["reply_to"]
        self.assertTrue(validate_email_address(reply_to), f"{reply_to} is not an address")

    # @feature alerts.email
    def test_the_body_names_the_alert_and_the_site(self):
        doc = self.alert(owner=self.AUTHOR)
        body = doc.evaluate_message({"rows": [], "count": 0, "datatable": ""})
        self.assertIn("Overdue invoices", body)
        self.assertIn(frappe.utils.get_url(allow_header_override=False), body)
        self.assertIn(self.AUTHOR, body)

    # @feature alerts.email
    def test_a_title_written_as_markup_stays_text_in_the_footer(self):
        doc = self.alert()
        doc.title = "<script>x</script>"
        body = doc.evaluate_message({"rows": [], "count": 0, "datatable": ""})
        self.assertNotIn("<script>x</script>", body)
        self.assertIn("&lt;script&gt;", body)


ALERT_TODO_PREFIX = "Insights Alert Test"


class AlertOverSeededTodos(InsightsIntegrationTestCase):
    """A query of three todos — two Open, one Closed — for a condition to read."""

    @classmethod
    def before_class(cls):
        cls.delete_todos()
        cls.todos = [
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"{ALERT_TODO_PREFIX} {status} {i}",
                    "status": status,
                }
            )
            .insert(ignore_permissions=True)
            .name
            for status, i in (("Open", 1), ("Open", 2), ("Closed", 3))
        ]
        cls.workbook = create_test_workbook("Administrator", title="Alert Workbook").name
        cls.query = create_test_query(
            "Administrator",
            cls.workbook,
            title="Alert Query",
            operations=[
                {
                    "type": "source",
                    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
                },
                {
                    "type": "filter",
                    "column": {"type": "column", "column_name": "description"},
                    "operator": "contains",
                    "value": ALERT_TODO_PREFIX,
                },
                {
                    "type": "order_by",
                    "column": {"type": "column", "column_name": "description"},
                    "direction": "asc",
                },
            ],
        ).name
        # The query reads tabToDo over the data source's own connection, which cannot see this transaction.
        frappe.db.commit()  # nosemgrep

    @classmethod
    def after_class(cls):
        frappe.delete_doc("Insights Workbook", cls.workbook, force=True)
        cls.delete_todos()
        # before_class committed, so the runner's rollback leaves these rows behind.
        frappe.db.commit()  # nosemgrep

    @staticmethod
    def delete_todos():
        for name in frappe.get_all(
            "ToDo", filters={"description": ["like", f"{ALERT_TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)

    def make_alert(self, **fields):
        doc = frappe.new_doc("Insights Alert")
        doc.update(
            {
                "title": "Open todos",
                "channel": "Email",
                "query": self.query,
                "frequency": "Daily",
                "custom_condition": 1,
                "condition": "status == 'Open'",
                "message": "hello",
                "recipients": "someone@external.example.org",
                **fields,
            }
        )
        doc.insert()
        self.addCleanup(frappe.delete_doc, "Insights Alert", doc.name, force=True)
        return doc


class TestCondition(AlertOverSeededTodos):
    """What the condition decides, and what a test send overrides."""

    # @feature alerts.condition
    def test_an_alert_fires_when_a_row_meets_its_condition_and_stays_quiet_when_none_does(self):
        met = self.make_alert(condition="status == 'Open'")
        unmet = self.make_alert(condition="status == 'Nowhere'")

        with patch("frappe.sendmail") as sendmail:
            met.send_alert()
        self.assertEqual(sendmail.call_count, 1)
        self.assertEqual(sendmail.call_args.kwargs["recipients"], ["someone@external.example.org"])

        with patch("frappe.sendmail") as sendmail:
            unmet.send_alert()
        self.assertEqual(sendmail.call_count, 0)

    # @feature alerts.condition
    def test_a_condition_that_does_not_parse_refuses_the_save(self):
        with self.assertRaises(frappe.ValidationError) as refusal:
            self.make_alert(condition="status ==")

        self.assertIn("Invalid condition", str(refusal.exception))

    # @feature alerts.test-send
    def test_a_test_send_delivers_even_when_the_condition_is_not_met_and_when_the_alert_is_not_due(
        self,
    ):
        alert = self.make_alert(condition="status == 'Nowhere'")
        alert.db_set("last_execution", now_datetime(), update_modified=False)
        alert.reload()

        self.assertFalse(alert.is_event_due())

        with patch("frappe.sendmail") as sendmail:
            alert.test_alert()

        self.assertEqual(sendmail.call_count, 1)

    # @feature alerts.message
    def test_the_message_prints_the_field_tokens_and_the_rows_table(self):
        alert = self.make_alert(message="First: {{ rows[0].description }}\n\n{{ rows }}")

        body = alert.evaluate_message(alert.get_message_context())

        self.assertIn(f"First: {ALERT_TODO_PREFIX} Closed 3", body)
        for status, i in (("Open", 1), ("Open", 2), ("Closed", 3)):
            self.assertIn(f"{ALERT_TODO_PREFIX} {status} {i}", body)
        self.assertIn("<table", body)


class TestSchedule(AlertOverSeededTodos):
    """When an alert is next due."""

    # @feature alerts.create
    def test_a_new_alert_is_due_by_its_frequency_and_a_cron_alert_by_its_expression(self):
        daily = self.make_alert(frequency="Daily")

        daily.last_execution = "2026-01-01 10:00:00"
        self.assertEqual(daily.next_execution, "2026-01-02 00:00:00.000000")
        self.assertTrue(daily.is_event_due())

        daily.last_execution = now_datetime()
        self.assertFalse(daily.is_event_due())

        every_minute = self.make_alert(frequency="Cron", cron_format="* * * * *")

        every_minute.last_execution = add_to_date(now_datetime(), minutes=-2)
        self.assertTrue(every_minute.is_event_due())

        every_minute.last_execution = add_to_date(now_datetime(), minutes=2)
        self.assertFalse(every_minute.is_event_due())


class TestTelegram(AlertOverSeededTodos):
    """Telegram is an external service, so the bot is where the test stops."""

    def set_token(self, token):
        settings = frappe.get_single("Insights Settings")
        was = settings.get_password("telegram_api_token", raise_exception=False)
        settings.telegram_api_token = token
        settings.save(ignore_permissions=True)
        self.addCleanup(self.restore_token, was)

    def restore_token(self, was):
        settings = frappe.get_single("Insights Settings")
        settings.telegram_api_token = was
        settings.save(ignore_permissions=True)

    # @feature alerts.telegram
    def test_a_telegram_alert_sends_the_rendered_message_to_its_chat(self):
        self.set_token("bot-token")
        alert = self.make_alert(
            channel="Telegram",
            telegram_chat_id="-100123",
            recipients="",
            message="{{ count }} open todos",
        )

        with patch("telegram.Bot") as bot:
            alert.send_alert(force=True)

        bot.assert_called_once_with(token="bot-token")
        bot.return_value.send_message.assert_called_once_with(chat_id="-100123", text="3 open todos")
