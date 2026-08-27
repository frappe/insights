# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import validate_email_address

from insights.insights.doctype.insights_alert.insights_alert import InsightsAlert
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
)

MESSAGE_CONTEXT = {"rows": [], "count": 0, "datatable": ""}


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

    def test_an_address_outside_this_site_is_a_recipient(self):
        """A report goes to a client or an accountant as often as to a colleague."""
        self.assertEqual(self.email_alert(self.OUTSIDER).get_recipients(), [self.OUTSIDER])

    def test_a_list_is_split_and_trimmed(self):
        alert = self.email_alert(f" {self.MEMBER} , {self.OUTSIDER} ")
        self.assertEqual(alert.get_recipients(), [self.MEMBER, self.OUTSIDER])

    def test_an_empty_list_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.email_alert("  ,  ").get_recipients()

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

    def body_of(self, doc):
        with patch.object(InsightsAlert, "get_message_context", return_value=MESSAGE_CONTEXT):
            return doc.evaluate_message()

    def test_a_reply_reaches_the_author(self):
        doc = self.alert(owner=self.AUTHOR)
        with patch("frappe.sendmail") as sendmail:
            doc.send_email_alert("hello")
        self.assertEqual(sendmail.call_args.kwargs["reply_to"], self.AUTHOR)

    def test_an_admin_owned_alert_replies_to_an_address(self):
        """`owner` is a User name, and for the admin that name is
        "Administrator". `sendmail` refuses a reply_to it cannot parse."""
        doc = self.alert()
        self.assertEqual(doc.owner, "Administrator")
        with patch("frappe.sendmail") as sendmail:
            doc.send_email_alert("hello")
        reply_to = sendmail.call_args.kwargs["reply_to"]
        self.assertTrue(validate_email_address(reply_to), f"{reply_to} is not an address")

    def test_the_body_names_the_alert_and_the_site(self):
        body = self.body_of(self.alert(owner=self.AUTHOR))
        self.assertIn("Overdue invoices", body)
        self.assertIn(frappe.utils.get_url(allow_header_override=False), body)
        self.assertIn(self.AUTHOR, body)

    def test_a_title_written_as_markup_stays_text_in_the_footer(self):
        doc = self.alert()
        doc.title = "<script>x</script>"
        body = self.body_of(doc)
        self.assertNotIn("<script>x</script>", body)
        self.assertIn("&lt;script&gt;", body)
