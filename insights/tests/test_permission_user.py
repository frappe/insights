"""A preview and an alert each run as a stored user.

Neither has a caller to take permissions from. So each stores a user: a preview
key when it is generated, an alert when it is enabled. The engine filters rows
by that user. The session user does not change, so nothing here may call
`frappe.set_user`.

A public link uses Run as owner instead. `test_run_as_owner` covers it.

The fixtures below sit on `tabToDo`, whose permission query restricts a
non-System-Manager to their own assignments. That is the row-level difference
every test turns on.
"""

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.permission_user import get_permission_user, permission_user
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
    delete_workbooks,
)

PUBLISHER = "permission_user_publisher@test.com"
EDITOR = "permission_user_editor@test.com"

WORKBOOK_TITLE = "Permission User Test Workbook"
TODO_PREFIX = "Permission User Test"


def todo_operations():
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
        },
        {
            "type": "filter",
            "column": {"type": "column", "column_name": "description"},
            "operator": "contains",
            "value": TODO_PREFIX,
        },
    ]


class TestPreviewKeyNamesItsUser(InsightsIntegrationTestCase):
    """A preview has no caller, so the key stores the user it was generated for."""

    @classmethod
    def before_class(cls):
        delete_users(PUBLISHER)
        create_user(PUBLISHER, first_name="Perm", last_name="Publisher", roles="Insights User")

    @classmethod
    def after_class(cls):
        delete_users(PUBLISHER)

    # @feature dashboard.preview-image
    def test_a_preview_key_names_the_user_it_was_cut_for(self):
        from insights.preview_key import cache_key, generate_preview_key

        with as_user(PUBLISHER), generate_preview_key("some-dashboard") as key:
            stored = frappe.cache.get_value(cache_key(key))

        self.assertEqual(stored, {"dashboard": "some-dashboard", "user": PUBLISHER})


def error_log_operations():
    """A query over `tabError Log`, which an Insights User may not read at all."""
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabError Log"},
        }
    ]


def user_operations():
    """A query over `tabUser`, which an Insights User may not read at large."""
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabUser"},
        }
    ]


class TestAlertRunsAsItsEnabler(InsightsIntegrationTestCase):
    """The scheduler runs as Administrator and `validate` sees the query as it
    was at save, so the owner could point it elsewhere afterwards."""

    @classmethod
    def before_class(cls):
        cls.cleanup()
        create_user(PUBLISHER, first_name="Perm", last_name="Publisher", roles="Insights User")
        create_user(EDITOR, first_name="Perm", last_name="Editor", roles="Insights User")
        cls.workbook = create_test_workbook(PUBLISHER, title=WORKBOOK_TITLE).name
        cls.query = create_test_query(
            PUBLISHER, cls.workbook, title="Alert Query", operations=todo_operations()
        ).name

    @classmethod
    def after_class(cls):
        cls.cleanup()

    @classmethod
    def cleanup(cls):
        for alert in frappe.get_all(
            "Insights Alert", filters={"title": ["like", f"%{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("Insights Alert", alert, force=True, ignore_permissions=True)
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        delete_users(PUBLISHER, EDITOR)

    def create_alert(self, author=PUBLISHER, query=None):
        with as_user(author), db_connections():
            alert = frappe.get_doc(
                {
                    "doctype": "Insights Alert",
                    "title": f"{TODO_PREFIX} Alert",
                    "query": query or self.query,
                    "channel": "Email",
                    "recipients": PUBLISHER,
                    "frequency": "Daily",
                    "custom_condition": 1,
                    "condition": "q['status'] == 'Open'",
                    "message": "{{ rows }}",
                }
            ).insert()
        self.addCleanup(frappe.delete_doc, "Insights Alert", alert.name, force=True)
        return alert

    def repoint_query(self, operations):
        frappe.db.set_value(DT.QUERY, self.query, "operations", frappe.as_json(operations))
        frappe.clear_document_cache(DT.QUERY, self.query)

    # @feature alerts.failed-run-recorded alerts.enable
    def test_an_alert_that_cannot_run_tells_its_owner(self):
        """The enabler may not read the table the query now uses. The error used
        to reach only the Error Log."""
        from unittest.mock import patch

        from insights.insights.doctype.insights_alert.insights_alert import send_alerts

        alert = self.create_alert()
        self.repoint_query(error_log_operations())

        # `send_alerts` rolls back on error. Commit the alert and its query so
        # they still exist after the failure.
        frappe.db.commit()  # nosemgrep

        def restore():
            frappe.delete_doc("Insights Alert", alert.name, force=True, ignore_permissions=True)
            self.repoint_query(todo_operations())
            frappe.db.commit()  # nosemgrep

        self.addCleanup(restore)

        with patch("frappe.sendmail") as sendmail:
            send_alerts()

        told = [
            call.kwargs for call in sendmail.call_args_list if call.kwargs.get("recipients") == [PUBLISHER]
        ]
        self.assertEqual(len(told), 1)
        self.assertIn(alert.title, told[0]["subject"])

    # @feature alerts.enable permissions.member-write-follows-workbook
    def test_an_alert_stops_sending_once_its_enabler_may_not_write_it(self):
        """The scheduler runs as Administrator, with the enabler as permission
        user. An editor who made the query and the alert, and then left the
        workbook, owns both but may write neither. So the alert stops sending."""
        from unittest.mock import patch

        from insights.api.workbooks import update_share_permissions
        from insights.insights.doctype.insights_alert.insights_alert import InsightsAlert

        with as_user(PUBLISHER):
            update_share_permissions(self.workbook, [{"user": EDITOR, "read": 1, "write": 1}])
        query = create_test_query(EDITOR, self.workbook, title="Editor Query", operations=todo_operations())
        alert = self.create_alert(author=EDITOR, query=query.name)
        self.assertEqual(alert.permission_user, EDITOR)

        def scheduled_send():
            with (
                as_user("Administrator"),
                permission_user(alert.permission_user),
                patch.object(InsightsAlert, "evaluate_condition", return_value=True),
                patch.object(InsightsAlert, "get_message_context", return_value={"rows": [], "count": 0}),
                patch("frappe.sendmail") as sendmail,
            ):
                frappe.get_doc("Insights Alert", alert.name).send_alert()
            return sendmail.call_count

        self.assertEqual(scheduled_send(), 1)

        with as_user(PUBLISHER):
            update_share_permissions(self.workbook, [])
        with self.assertRaises(frappe.PermissionError):
            scheduled_send()

    def scheduled_run(self, alert):
        """Runs `send_alerts` as the scheduler does, with the alert due."""
        from unittest.mock import patch

        from insights.insights.doctype.insights_alert.insights_alert import InsightsAlert, send_alerts

        frappe.db.set_value("Insights Alert", alert.name, "last_execution", None)
        frappe.db.commit()  # nosemgrep
        with (
            patch.object(InsightsAlert, "evaluate_condition", return_value=True),
            patch.object(InsightsAlert, "get_message_context", return_value={"rows": [], "count": 0}),
            patch("frappe.sendmail") as sendmail,
        ):
            send_alerts()
        return [
            (call.kwargs["recipients"], call.kwargs["subject"], call.kwargs["message"])
            for call in sendmail.call_args_list
        ]

    def assert_stopped_and_told(self, alert, mails, cause):
        self.assertEqual(len(mails), 1, mails)
        recipients, subject, message = mails[0]
        self.assertEqual(recipients, [PUBLISHER])
        self.assertEqual(subject, f"Insights Alert stopped: {alert.title}")
        self.assertIn(EDITOR, message)
        self.assertIn(cause, message)
        self.assertNotIn("try again", message)
        self.assertEqual(frappe.db.get_value("Insights Alert", alert.name, "disabled"), 1)
        self.assertEqual(self.scheduled_run(alert), [])

    # @feature alerts.failed-run-recorded alerts.enable
    def test_an_alert_whose_enabler_is_disabled_stops_and_tells_the_workbook_owner(self):
        """The alert runs as the editor who enabled it, not the publisher who
        made it."""
        from insights.api.workbooks import update_share_permissions

        with as_user(PUBLISHER):
            update_share_permissions(self.workbook, [{"user": EDITOR, "read": 1, "write": 1}])
        alert = self.create_alert()
        with as_user(EDITOR), db_connections():
            for disabled in (1, 0):
                doc = frappe.get_doc("Insights Alert", alert.name)
                doc.disabled = disabled
                doc.save()
        self.assertEqual(frappe.db.get_value("Insights Alert", alert.name, "permission_user"), EDITOR)
        frappe.db.commit()  # nosemgrep

        def restore():
            frappe.db.set_value("User", EDITOR, "enabled", 1)
            frappe.delete_doc("Insights Alert", alert.name, force=True, ignore_permissions=True)
            with as_user(PUBLISHER):
                update_share_permissions(self.workbook, [])
            frappe.db.commit()  # nosemgrep

        self.addCleanup(restore)

        self.assertEqual(
            [mail[:2] for mail in self.scheduled_run(alert)],
            [([PUBLISHER], f"Insights Alert: {alert.title}")],
        )

        frappe.db.set_value("User", EDITOR, "enabled", 0)
        frappe.clear_cache(user=EDITOR)
        self.assert_stopped_and_told(alert, self.scheduled_run(alert), "is disabled")

    # @feature alerts.failed-run-recorded alerts.enable
    def test_an_alert_whose_enabler_left_the_workbook_stops_and_tells_the_workbook_owner(self):
        """The editor made the alert, so they are its owner. After they leave the
        workbook, the notice goes to the workbook's owner instead."""
        from insights.api.workbooks import update_share_permissions

        with as_user(PUBLISHER):
            update_share_permissions(self.workbook, [{"user": EDITOR, "read": 1, "write": 1}])
        alert = self.create_alert(author=EDITOR)
        frappe.db.commit()  # nosemgrep

        def restore():
            frappe.delete_doc("Insights Alert", alert.name, force=True, ignore_permissions=True)
            with as_user(PUBLISHER):
                update_share_permissions(self.workbook, [])
            frappe.db.commit()  # nosemgrep

        self.addCleanup(restore)

        with as_user(PUBLISHER):
            update_share_permissions(self.workbook, [])
        frappe.db.commit()  # nosemgrep
        self.assert_stopped_and_told(alert, self.scheduled_run(alert), WORKBOOK_TITLE)

    # @feature alerts.enable
    def test_enabling_an_alert_records_who_enabled_it(self):
        alert = self.create_alert()
        self.assertEqual(frappe.db.get_value("Insights Alert", alert.name, "permission_user"), PUBLISHER)

    # @feature alerts.enable
    def test_an_ordinary_save_does_not_hand_over_the_alert(self):
        """Anyone with write on the alert's query may save it, so a title edit
        must not give the alert the editor's row access."""
        alert = self.create_alert()

        with as_user("Administrator"), db_connections():
            doc = frappe.get_doc("Insights Alert", alert.name)
            doc.title = f"{TODO_PREFIX} Alert renamed"
            doc.save()

        self.assertEqual(frappe.db.get_value("Insights Alert", alert.name, "permission_user"), PUBLISHER)

    # @feature alerts.enable
    def test_re_enabling_an_alert_records_who_re_enabled_it(self):
        alert = self.create_alert()
        frappe.db.set_value("Insights Alert", alert.name, "disabled", 1)

        with as_user("Administrator"), db_connections():
            doc = frappe.get_doc("Insights Alert", alert.name)
            doc.disabled = 0
            doc.save()

        self.assertEqual(
            frappe.db.get_value("Insights Alert", alert.name, "permission_user"), "Administrator"
        )

    # @feature alerts.enable
    def test_a_query_swapped_after_validation_still_runs_as_the_enabler(self):
        alert = self.create_alert()

        # the owner repoints the query at `tabUser` once validate() has passed it
        self.repoint_query(user_operations())
        self.addCleanup(self.repoint_query, todo_operations())

        with as_user("Administrator"):
            doc = frappe.get_doc("Insights Alert", alert.name)
            unguarded = doc.get_message_context()
            with permission_user(alert.permission_user) as user:
                self.assertEqual(user, PUBLISHER)
                guarded = doc.get_message_context()

        self.assertGreater(unguarded["count"], guarded["count"])
        self.assertEqual(get_permission_user(), "Administrator")
