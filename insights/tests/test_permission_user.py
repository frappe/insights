"""A preview and an alert each run as somebody.

Neither has a caller whose permissions can decide the rows, so each names a user
at the moment the privileged act happened — minting a preview key, enabling an
alert. The engine filters by that user, and the session user is left alone, so
nothing here may call `frappe.set_user`.

A public link names its user another way. Content declares its own
`apply_user_permissions`, and `test_apply_user_permissions` is where that is held.

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
    """A preview has no caller, so the key carries the user it was cut for."""

    @classmethod
    def before_class(cls):
        delete_users(PUBLISHER)
        create_user(PUBLISHER, first_name="Perm", last_name="Publisher", roles="Insights User")

    @classmethod
    def after_class(cls):
        delete_users(PUBLISHER)

    # @feature dashboard.preview-image
    def test_a_preview_key_names_the_user_it_was_cut_for(self):
        from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
            generate_preview_key,
        )

        with as_user(PUBLISHER), generate_preview_key("some-dashboard") as key:
            stored = frappe.cache.get_value(f"insights_preview_key:{key}")

        self.assertEqual(stored, {"dashboard": "some-dashboard", "user": PUBLISHER})


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
        delete_users(PUBLISHER)

    def create_alert(self):
        with as_user(PUBLISHER), db_connections():
            alert = frappe.get_doc(
                {
                    "doctype": "Insights Alert",
                    "title": f"{TODO_PREFIX} Alert",
                    "query": self.query,
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
