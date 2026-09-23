# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
import requests
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime, validate_email_address

from insights.http import OutboundRequestRefused
from insights.insights.doctype.insights_alert.insights_alert import (
    ALERT_MAX_ROWS,
    InsightsAlert,
    send_alerts,
)
from insights.permission_user import permission_user
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    as_user,
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
        payload, _ = self.post_one(message_context(row_count=ALERT_MAX_ROWS + 150))
        self.assertEqual(len(payload["context"]["rows"]), ALERT_MAX_ROWS)
        self.assertEqual(payload["context"]["count"], ALERT_MAX_ROWS + 150)
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

    # @feature alerts.failed-run-recorded
    def test_the_owner_is_told_a_run_failed_and_not_why(self):
        """`send_alerts` mails the owner. The scheduler's session is
        Administrator, so a connection error was composed for someone who may
        configure the source, naming its host; that stays in the Error Log."""
        frappe.db.set_value("Insights Alert", self.alert.name, "last_execution", None)
        # `send_alerts` rolls back what it catches
        frappe.db.commit()  # nosemgrep
        detail = "Can't connect to MySQL server on '10.0.4.12'"

        with (
            patch.object(InsightsAlert, "evaluate_condition", side_effect=frappe.ValidationError(detail)),
            patch("frappe.sendmail") as sendmail,
        ):
            send_alerts()

        message = sendmail.call_args.kwargs["message"]
        self.assertIn(self.alert.title, message)
        self.assertNotIn("10.0.4.12", message)
        self.assertTrue(frappe.db.exists("Error Log", {"method": f"Failed to send alert: {self.alert.name}"}))


class ATickRunsEveryAlert(InsightsIntegrationTestCase):
    """`send_alerts`, the scheduler's four-minute tick. What it does after one
    alert fails writes and commits too, and a failure there must not cost the
    alerts after it their window."""

    @classmethod
    def before_class(cls):
        cls.workbook = create_test_workbook("Administrator", title="Alert Tick Workbook")
        query = create_test_query("Administrator", cls.workbook.name, title="Alert Tick Query")
        cls.alerts = [
            frappe.get_doc(
                doctype="Insights Alert",
                title=f"Alert Tick {index}",
                channel="Webhook",
                query=query.name,
                frequency="Daily",
                condition="q['status'] == 'Open'",
                custom_condition=1,
                message="{{ rows }}",
                webhook_url="https://example.com/hooks/insights",
                webhook_token="sekret-token",
            )
            .insert()
            .name
            for index in (1, 2)
        ]

    @classmethod
    def after_class(cls):
        for name in cls.alerts:
            frappe.delete_doc("Insights Alert", name, force=True)
        frappe.delete_doc("Insights Workbook", cls.workbook.name, force=True)

    def tried(self, refusal, aftermath: str) -> list[str]:
        """The alerts of this class the tick tried, when every send is refused
        with `refusal` and `aftermath` raises."""
        tried = []

        def send(alert):
            tried.append(alert.name)
            raise refusal

        module = "insights.insights.doctype.insights_alert.insights_alert"
        with (
            patch.object(InsightsAlert, "is_event_due", return_value=True),
            patch.object(InsightsAlert, "send_alert", autospec=True, side_effect=send),
            patch(f"{module}.{aftermath}", side_effect=frappe.QueryDeadlockError("deadlock")),
        ):
            send_alerts()

        return sorted(name for name in tried if name in self.alerts)

    # @feature alerts.failed-run-recorded
    def test_a_failed_record_of_a_failed_run_does_not_stop_the_tick(self):
        self.assertEqual(self.tried(requests.ConnectionError("down"), "record_execution"), self.alerts)

    # @feature alerts.failed-run-recorded
    def test_a_failed_stop_of_a_refused_alert_does_not_stop_the_tick(self):
        from insights.insights.doctype.insights_alert.insights_alert import SendRefused

        self.assertEqual(self.tried(SendRefused("disabled"), "stop"), self.alerts)


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


class TestRowsAnAlertCarries(AlertOverSeededTodos):
    # @feature alerts.message alerts.webhook
    def test_the_rows_stop_at_the_cap_and_the_count_is_the_whole_result(self):
        """`send_alert` builds one context for every channel, so the count it
        reports is the query's and not the page's, and a mail says what it left out."""
        alert = self.make_alert(message="{{ count }} open\n\n{{ rows }}")

        with patch(f"{InsightsAlert.__module__}.ALERT_MAX_ROWS", 2):
            context = alert.get_message_context()

        self.assertEqual(context["count"], 3)
        self.assertEqual(len(context["rows"]), 2)
        body = alert.evaluate_message(context)
        self.assertIn("3 open", body)
        self.assertIn("The first 2 of 3 rows", body)

    # @feature alerts.message alerts.webhook
    def test_the_rows_and_the_count_are_read_when_the_condition_fires(self):
        """`send_alert` builds its message from `get_message_context` after the
        condition, which reads the table fresh. An author's earlier run caches
        rows and count under two lifetimes, so the mail read either one stale."""
        query = frappe.get_doc("Insights Query v3", self.query)
        query.execute(page_size=ALERT_MAX_ROWS)
        query.count_rows()

        todo = frappe.get_doc(
            {"doctype": "ToDo", "description": f"{ALERT_TODO_PREFIX} Open 4", "status": "Open"}
        ).insert(ignore_permissions=True)
        # the query reads over the data source's own connection
        frappe.db.commit()  # nosemgrep
        self.addCleanup(frappe.db.commit)  # nosemgrep
        self.addCleanup(frappe.delete_doc, "ToDo", todo.name, force=True, ignore_permissions=True)

        context = self.make_alert().get_message_context()

        self.assertEqual(context["count"], 4)
        self.assertIn(f"{ALERT_TODO_PREFIX} Open 4", [row["description"] for row in context["rows"]])

    # @feature alerts.condition alerts.message
    def test_a_script_query_is_read_fresh_for_the_condition_and_the_count(self):
        """`send_alert` decides on `evaluate_condition` and mails
        `get_message_context`. A script's output is cached apart from the SQL
        over it, so an earlier run fired the condition and printed the count
        off rows the script no longer returns."""
        script = self.make_script_query(
            "results = frappe.get_all('ToDo', "
            f"filters={{'description': ['like', '{ALERT_TODO_PREFIX} Script%']}}, "
            "fields=['description', 'status'])"
        )
        closed = frappe.get_doc(
            {"doctype": "ToDo", "description": f"{ALERT_TODO_PREFIX} Script 1", "status": "Closed"}
        ).insert(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "ToDo", closed.name, force=True, ignore_permissions=True)
        alert = self.make_alert(query=script, condition="status == 'Open'")
        # an author's run of the query, and an earlier tick
        frappe.get_doc("Insights Query v3", script).execute()
        self.assertFalse(alert.evaluate_condition())

        opened = frappe.get_doc(
            {"doctype": "ToDo", "description": f"{ALERT_TODO_PREFIX} Script 2", "status": "Open"}
        ).insert(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "ToDo", opened.name, force=True, ignore_permissions=True)

        self.assertTrue(alert.evaluate_condition())
        self.assertEqual(alert.get_message_context()["count"], 2)

    def make_script_query(self, code):
        return create_test_query(
            "Administrator",
            self.workbook,
            title="Alert Script Query",
            operations=[{"type": "code", "code": code}],
        ).name


class TestWhoMaySend(AlertOverSeededTodos):
    """Sending mails the author's recipients, so it asks for more than reading
    the alert, and the user it runs as is asked again at every send."""

    READER = "alert_reader@test.com"

    @classmethod
    def before_class(cls):
        super().before_class()
        create_user(cls.READER, first_name="Alert", last_name="Reader", roles="Insights User")

    @classmethod
    def after_class(cls):
        super().after_class()
        delete_users(cls.READER)

    # @feature alerts.test-send
    def test_a_collaborator_who_may_only_read_the_alert_cannot_send_it(self):
        """`AlertSetupDialog` calls `test_alert` through `run_doc_method`, which
        checks read only; the desk form calls `send_alert` the same way."""
        from insights.api.workbooks import update_share_permissions

        alert = self.make_alert(condition="status == 'Open'")
        update_share_permissions(self.workbook, [{"user": self.READER, "read": 1, "write": 0}])

        with as_user(self.READER), patch("frappe.sendmail") as sendmail:
            stored = frappe.get_doc("Insights Alert", alert.name)
            self.assertTrue(stored.has_permission("read"))
            for send in (stored.test_alert, stored.send_alert):
                with self.subTest(send.__name__), self.assertRaises(frappe.PermissionError):
                    send()

        self.assertEqual(sendmail.call_count, 0)
        self.assertIsNone(frappe.db.get_value("Insights Alert", alert.name, "last_execution"))

    # @feature alerts.test-send
    def test_an_unsaved_alert_is_sent_by_a_writer_of_its_workbook_only(self):
        """`QueryAlertsDialog` calls `test_alert` through `run_doc_method` on an
        alert it has not saved yet, named `new-alert-…`. A reader of the
        workbook may send the same payload with recipients of their choosing."""
        from insights.api.workbooks import update_share_permissions

        def send_unsaved(name):
            alert = frappe.new_doc("Insights Alert")
            alert.update(
                {
                    "title": "Open todos",
                    "channel": "Email",
                    "query": self.query,
                    "frequency": "Daily",
                    "custom_condition": 1,
                    "condition": "status == 'Open'",
                    "message": "hello",
                    "recipients": "someone@external.example.org",
                }
            )
            alert.name = name
            with as_user(self.READER), patch("frappe.sendmail") as sendmail:
                alert.test_alert()
            return sendmail.call_count

        for name in (None, "new-alert-abc123"):
            with self.subTest(name=name):
                update_share_permissions(self.workbook, [{"user": self.READER, "read": 1, "write": 0}])
                with self.assertRaises(frappe.PermissionError):
                    send_unsaved(name)

                update_share_permissions(self.workbook, [{"user": self.READER, "read": 1, "write": 1}])
                self.assertEqual(send_unsaved(name), 1)

    # @feature alerts.enable
    def test_an_edit_by_another_writer_keeps_the_enabler_and_the_form_names_them(self):
        """`AlertSetupDialog` reads `permission_user` through `insights.api.get_doc`
        to say who the alert runs as. Ruling Q11: writers are trusted, so an edit
        does not move it."""
        from insights.api import get_doc
        from insights.api.workbooks import update_share_permissions

        alert = self.make_alert()
        update_share_permissions(self.workbook, [{"user": self.READER, "read": 1, "write": 1}])

        with as_user(self.READER):
            edited = frappe.get_doc("Insights Alert", alert.name)
            edited.recipients = self.READER
            edited.save()
            loaded = get_doc("Insights Alert", alert.name)

        self.assertEqual(loaded["permission_user"], "Administrator")

    # @feature alerts.enable
    def test_an_alert_whose_user_lost_the_query_sends_nothing(self):
        """`send_alerts` runs each alert as the user who enabled it. A share
        revoked since then reaches the next send, not only the next save."""
        from insights.api.workbooks import update_share_permissions

        alert = self.make_alert(condition="status == 'Open'")
        # enabled by the reader, who has since lost the workbook
        alert.db_set("permission_user", self.READER, update_modified=False)
        update_share_permissions(self.workbook, [])

        with permission_user(self.READER), patch("frappe.sendmail") as sendmail:
            with self.assertRaises(frappe.PermissionError):
                alert.send_alert()

        self.assertEqual(sendmail.call_count, 0)

    # @feature alerts.enable query.script
    def test_an_alerts_script_reads_as_the_user_who_enabled_it(self):
        """`send_alerts` enters `permission_user` for the enabler and reads the
        rows it mails through `get_message_context`. The scheduler's session is
        Administrator, and the script read as the session."""
        query = create_test_query(
            "Administrator",
            self.workbook,
            title="Alert Script Reader",
            operations=[{"type": "code", "code": "results = [{'user': frappe.session.user}]"}],
        ).name
        alert = self.make_alert(query=query, condition="user != ''")

        for runs_as in (self.READER, "Administrator"):
            with self.subTest(runs_as=runs_as), permission_user(runs_as):
                self.assertEqual([row["user"] for row in alert.get_message_context()["rows"]], [runs_as])
        self.assertEqual(frappe.session.user, "Administrator")


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
