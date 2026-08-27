"""A public link, a preview and an alert each run as somebody.

None of the three has a caller whose permissions can decide the rows, so each
names a user at the moment it was published or enabled. The engine filters by
that user. The session user is left alone, so nothing here may call
`frappe.set_user`.

The fixtures below sit on `tabToDo`, whose permission query restricts a
non-System-Manager to their own assignments. That is the row-level difference
every test turns on.
"""

from contextlib import contextmanager
from unittest.mock import patch

import frappe

from insights.api import run_doc_method
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.permission_user import get_permission_user, permission_user
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_chart,
    create_test_query,
    create_test_workbook,
    create_user,
    delete_users,
    delete_workbooks,
)

PUBLISHER = "permission_user_publisher@test.com"
BYSTANDER = "permission_user_bystander@test.com"

WORKBOOK_TITLE = "Permission User Test Workbook"
TODO_PREFIX = "Permission User Test"

PUBLISHER_TODOS = [f"{TODO_PREFIX} publisher 1", f"{TODO_PREFIX} publisher 2"]
BYSTANDER_TODOS = [f"{TODO_PREFIX} bystander 1"]


@contextmanager
def as_http_request():
    """`insights.api.run_doc_method` validates the HTTP method, so fake a request."""
    frappe.local.request = frappe._dict(method="POST", headers={})
    try:
        yield
    finally:
        del frappe.local.request


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


class TestPermissionUser(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.cleanup()
        create_user(PUBLISHER, first_name="Perm", last_name="Publisher", roles="Insights User")
        create_user(BYSTANDER, first_name="Perm", last_name="Bystander", roles="Insights User")

        for user, descriptions in ((PUBLISHER, PUBLISHER_TODOS), (BYSTANDER, BYSTANDER_TODOS)):
            for description in descriptions:
                frappe.get_doc(
                    {
                        "doctype": "ToDo",
                        "description": description,
                        "allocated_to": user,
                        "assigned_by": "Administrator",
                    }
                ).insert(ignore_permissions=True)

        cls.workbook = create_test_workbook(PUBLISHER, title=WORKBOOK_TITLE).name
        cls.query = create_test_query(
            PUBLISHER, cls.workbook, title="Permission User Query", operations=todo_operations()
        ).name
        cls.chart = create_test_chart(
            PUBLISHER, cls.workbook, query=cls.query, title="Permission User Chart"
        ).name

    @classmethod
    def after_class(cls):
        cls.cleanup()

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for todo in frappe.get_all(
            "ToDo", filters={"description": ["like", f"%{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        delete_users(PUBLISHER, BYSTANDER)

    def publish_dashboard(self, title):
        with as_user(PUBLISHER):
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": title,
                    "workbook": self.workbook,
                    "items": [{"id": "chart-1", "type": "chart", "chart": self.chart}],
                }
            ).insert()
            dashboard.update_access(
                {"is_public": 1, "is_shared_with_organization": 0, "people_with_access": []}
            )
        # a public dashboard on the shared chart is a root every other test here
        # would then resolve to, so it does not outlive the test that made it
        self.addCleanup(frappe.delete_doc, DT.DASHBOARD, dashboard.name, force=True)
        return dashboard.name

    def publish(self, user=PUBLISHER):
        with as_user(user):
            frappe.get_doc(DT.CHART, self.chart).update_access(is_public=True)
        self.addCleanup(
            frappe.db.set_value,
            DT.CHART,
            self.chart,
            {"is_public": 0, "permission_user": None},
        )

    def descriptions(self, result):
        return sorted(row["description"] for row in result["rows"])

    def run_as_guest(self, **kwargs):
        docs = frappe.as_json({"doctype": DT.QUERY, "name": self.query})
        kwargs.setdefault("docs", docs)
        with as_user("Guest"), db_connections(), as_http_request():
            return run_doc_method(method="execute", **kwargs)

    # publishing

    def test_publishing_records_the_publisher(self):
        self.publish()
        self.assertEqual(frappe.db.get_value(DT.CHART, self.chart, "permission_user"), PUBLISHER)

    def test_withdrawing_clears_the_publisher(self):
        self.publish()
        with as_user(PUBLISHER):
            frappe.get_doc(DT.CHART, self.chart).update_access(is_public=False)
        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "permission_user"))

    def test_a_plain_write_cannot_publish(self):
        """`is_public` is permlevel 1, so the generic write surface cannot reach it."""
        with as_user(PUBLISHER):
            chart = frappe.get_doc(DT.CHART, self.chart)
            chart.is_public = 1
            chart.save()

        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "is_public"))

    def test_a_plain_write_cannot_name_a_permission_user(self):
        with as_user(PUBLISHER):
            chart = frappe.get_doc(DT.CHART, self.chart)
            chart.permission_user = "Administrator"
            chart.save()

        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "permission_user"))

    def test_publishing_needs_share_access(self):
        with as_user(BYSTANDER), self.assertRaises(frappe.PermissionError):
            frappe.get_doc(DT.CHART, self.chart).update_access(is_public=True)

    # execution

    def test_a_public_link_returns_only_the_publisher_rows(self):
        self.publish()
        result = self.run_as_guest()
        self.assertEqual(self.descriptions(result), sorted(PUBLISHER_TODOS))

    def test_a_public_link_does_not_switch_the_session_user(self):
        self.publish()
        docs = frappe.as_json({"doctype": DT.QUERY, "name": self.query})

        with as_user("Guest"), db_connections(), as_http_request():
            with patch.object(frappe, "set_user", side_effect=AssertionError("set_user in a request")):
                result = run_doc_method(method="execute", docs=docs)
            self.assertEqual(frappe.session.user, "Guest")

        self.assertEqual(self.descriptions(result), sorted(PUBLISHER_TODOS))

    def test_the_permission_user_does_not_outlive_the_execution(self):
        self.publish()
        self.run_as_guest()
        self.assertEqual(get_permission_user(), frappe.session.user)

    def test_a_request_payload_cannot_name_its_own_permission_user(self):
        """`run_doc_method` builds the document from the body, so the user is
        read off the stored root instead."""
        self.publish()

        forged = frappe.get_doc(DT.QUERY, self.query).as_dict()
        forged.update({"permission_user": "Administrator", "owner": "Administrator"})

        result = self.run_as_guest(docs=frappe.as_json(forged))
        self.assertEqual(self.descriptions(result), sorted(PUBLISHER_TODOS))

    def test_a_request_argument_cannot_name_a_permission_user(self):
        self.publish()
        result = self.run_as_guest(args={"permission_user": "Administrator"})
        self.assertEqual(self.descriptions(result), sorted(PUBLISHER_TODOS))

    def test_a_link_that_names_nobody_is_refused(self):
        """Content published before the field existed, and never re-published."""
        self.publish()
        frappe.db.set_value(DT.CHART, self.chart, "permission_user", None)

        with self.assertRaises(frappe.PermissionError):
            self.run_as_guest()

    def test_a_chart_on_a_public_dashboard_runs_as_the_dashboard_publisher(self):
        from insights.api.shared import get_public_root

        with as_user(PUBLISHER):
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": f"{WORKBOOK_TITLE} Dashboard",
                    "workbook": self.workbook,
                    "items": [{"id": "chart-1", "type": "chart", "chart": self.chart}],
                }
            ).insert()
            dashboard.update_access(
                {"is_public": 1, "is_shared_with_organization": 0, "people_with_access": []}
            )

        # the chart itself was never published, so the dashboard is what names
        # the user its rows are filtered by
        self.assertFalse(frappe.db.get_value(DT.CHART, self.chart, "is_public"))
        self.assertEqual(get_public_root(DT.CHART, self.chart), (DT.DASHBOARD, dashboard.name))
        self.assertEqual(frappe.db.get_value(DT.DASHBOARD, dashboard.name, "permission_user"), PUBLISHER)

        result = self.run_as_guest()
        self.assertEqual(self.descriptions(result), sorted(PUBLISHER_TODOS))

    def test_a_chart_on_two_public_dashboards_picks_the_older_one(self):
        """The identity decides the rows, so an unordered `LIMIT 1` would make
        the same link answer differently on different days."""
        from insights.api.shared import get_public_root

        mine = [self.publish_dashboard(f"{WORKBOOK_TITLE} Holder {i}") for i in (1, 2)]

        holders = frappe.get_all("Insights Dashboard Chart v3", filters={"chart": self.chart}, pluck="parent")
        candidates = frappe.get_all(
            DT.DASHBOARD,
            filters={"name": ["in", holders], "is_public": 1},
            fields=["name", "creation"],
        )
        self.assertLessEqual(set(mine), {d.name for d in candidates})

        oldest = min(candidates, key=lambda d: d.creation).name
        for _ in range(3):
            self.assertEqual(get_public_root(DT.CHART, self.chart), (DT.DASHBOARD, oldest))

    def test_the_identity_decides_the_rows(self):
        """Two publishers, one chart, two different answers."""
        self.publish()
        as_publisher = self.descriptions(self.run_as_guest())

        frappe.db.set_value(DT.CHART, self.chart, "permission_user", BYSTANDER)
        as_bystander = self.descriptions(self.run_as_guest())

        self.assertEqual(as_publisher, sorted(PUBLISHER_TODOS))
        self.assertEqual(as_bystander, sorted(BYSTANDER_TODOS))

    # preview

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

    def test_enabling_an_alert_records_who_enabled_it(self):
        alert = self.create_alert()
        self.assertEqual(frappe.db.get_value("Insights Alert", alert.name, "permission_user"), PUBLISHER)

    def test_an_ordinary_save_does_not_hand_over_the_alert(self):
        """Anyone with write on the alert's query may save it, so a title edit
        must not give the alert the editor's row access."""
        alert = self.create_alert()

        with as_user("Administrator"), db_connections():
            doc = frappe.get_doc("Insights Alert", alert.name)
            doc.title = f"{TODO_PREFIX} Alert renamed"
            doc.save()

        self.assertEqual(frappe.db.get_value("Insights Alert", alert.name, "permission_user"), PUBLISHER)

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
