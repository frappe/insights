from contextlib import contextmanager
from unittest.mock import patch

import frappe
import ibis

from insights import user_permissions
from insights.api import run_doc_method as insights_run_doc_method
from insights.api.view import get_chart_data
from insights.api.workbooks import update_share_permissions
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    apply_user_permissions as filter_rows_for,
)
from insights.permission_user import get_permission_user, permission_user_for
from insights.permissions import can_read_rows
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

OWNER = "run_as_owner_owner@test.com"
READER = "run_as_owner_reader@test.com"
ADMIN = "run_as_owner_admin@test.com"
INSIGHTS_ADMIN = "run_as_owner_insights_admin@test.com"

WORKBOOK_TITLE = "Run As Owner Test Workbook"
TODO_PREFIX = "Run As Owner Test"

OWNER_TODOS = [f"{TODO_PREFIX} owner 1", f"{TODO_PREFIX} owner 2"]
READER_TODOS = [f"{TODO_PREFIX} reader 1"]

TEST_DS_TITLE = "Run As Owner Test DuckDB"
TEST_DS = frappe.scrub(TEST_DS_TITLE)


@contextmanager
def as_http_request():
    """`insights.api.run_doc_method` validates the HTTP method, so fake a request."""
    frappe.local.request = frappe._dict(method="POST", headers={})
    try:
        yield
    finally:
        del frappe.local.request


def todo_operations():
    """A query over `tabToDo`, narrowed to this module's fixtures.

    ToDo's permission query restricts non-System-Manager users to their own
    assignments, which is the row-level difference these tests turn on.
    """
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


class TestRunAsOwner(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.cleanup()
        create_user(OWNER, first_name="Permissions", last_name="Owner", roles="Insights User")
        create_user(READER, first_name="Permissions", last_name="Reader", roles="Insights User")
        create_user(ADMIN, first_name="Permissions", last_name="Admin", roles="System Manager")
        create_user(
            INSIGHTS_ADMIN,
            first_name="Permissions",
            last_name="Insights Admin",
            roles=["Insights User", "Insights Admin"],
        )

        for user, descriptions in ((OWNER, OWNER_TODOS), (READER, READER_TODOS)):
            for description in descriptions:
                frappe.get_doc(
                    {
                        "doctype": "ToDo",
                        "description": description,
                        "allocated_to": user,
                        "assigned_by": "Administrator",
                    }
                ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": DT.DATA_SOURCE,
                "title": TEST_DS_TITLE,
                "database_type": "DuckDB",
                "database_name": "run_as_owner_test_duckdb",
            }
        ).insert()

        cls.workbook, cls.query, cls.chart = cls.create_content()

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
        if frappe.db.exists(DT.DATA_SOURCE, TEST_DS):
            frappe.delete_doc(DT.DATA_SOURCE, TEST_DS, force=True)
        delete_users(OWNER, READER, ADMIN, INSIGHTS_ADMIN)

    @classmethod
    def create_content(cls):
        """A chart owned by OWNER, readable by READER and INSIGHTS_ADMIN through a read-only share."""
        with as_user(OWNER):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Run As Owner Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Run As Owner Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    # one row per description, which is the column these tests read
                    "config": {
                        "rows": [
                            {
                                "column_name": "description",
                                "dimension_name": "description",
                                "data_type": "String",
                            }
                        ],
                        "columns": [],
                        "values": [],
                        "order_by": [],
                    },
                }
            ).insert()
            update_share_permissions(
                workbook.name,
                [{"user": user, "read": 1, "write": 0} for user in (READER, INSIGHTS_ADMIN)],
            )

        return workbook, query, frappe.get_doc(DT.CHART, chart.name)

    def set_run_as_owner(self, value):
        frappe.db.set_value(DT.CHART, self.chart.name, "run_as_owner", value)
        self.addCleanup(frappe.db.set_value, DT.CHART, self.chart.name, "run_as_owner", 0)

    def fetch_chart_data(self, user):
        with as_user(user), db_connections():
            return get_chart_data(chart=self.chart.name, force=True)

    # @feature permissions.chart-run-as-owner
    def test_a_chart_runs_as_its_reader_by_default(self):
        chart = frappe.get_doc(DT.CHART, self.chart.name)
        self.assertFalse(chart.run_as_owner)

        with as_user(READER):
            self.assertEqual(permission_user_for(frappe.get_doc(DT.CHART, chart.name)), READER)

    # @feature permissions.card-says-it-is-scoped
    def test_a_card_names_the_user_permissions_that_narrowed_its_rows(self):
        """A scoped number reads as the whole one unless the card says otherwise."""
        self.assertNotIn("user_permissions", self.fetch_chart_data(READER))

        extra = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": f"{TODO_PREFIX} reader 2",
                "allocated_to": READER,
                "assigned_by": "Administrator",
            }
        ).insert(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "ToDo", extra.name, force=True, ignore_permissions=True)

        allowed = frappe.get_all("ToDo", filters={"description": READER_TODOS[0]}, pluck="name")[0]
        permission = frappe.get_doc(
            {"doctype": "User Permission", "user": READER, "allow": "ToDo", "for_value": allowed}
        ).insert(ignore_permissions=True)
        self.addCleanup(
            frappe.delete_doc, "User Permission", permission.name, force=True, ignore_permissions=True
        )

        result = self.fetch_chart_data(READER)

        self.assertEqual(self.descriptions(result), sorted(READER_TODOS))
        self.assertEqual(result["user_permissions"], [{"doctype": "ToDo", "documents": [allowed]}])

    # @feature permissions.card-says-it-is-scoped
    def test_a_card_never_names_the_documents_somebody_elses_grant_named(self):
        """A chart running as its owner narrowed by the owner's grants. Those
        name customers, companies or territories the reader was never published,
        and they are not a restriction the reader holds."""
        self.restrict(OWNER, OWNER_TODOS[0])
        self.set_run_as_owner(1)

        result = self.fetch_chart_data(READER)

        self.assertEqual(self.descriptions(result), [OWNER_TODOS[0]])
        self.assertNotIn("user_permissions", result)

    def restrict(self, user, description):
        """Narrow `user` to the one ToDo `description` names."""
        allowed = frappe.get_all("ToDo", filters={"description": description}, pluck="name")[0]
        permission = frappe.get_doc(
            {"doctype": "User Permission", "user": user, "allow": "ToDo", "for_value": allowed}
        ).insert(ignore_permissions=True)
        self.addCleanup(
            frappe.delete_doc, "User Permission", permission.name, force=True, ignore_permissions=True
        )
        return allowed

    # @feature permissions.chart-run-as-owner
    def test_a_chart_run_as_its_reader_filters_rows_per_session_user(self):
        self.set_run_as_owner(0)

        owner_rows = self.descriptions(self.fetch_chart_data(OWNER))
        reader_rows = self.descriptions(self.fetch_chart_data(READER))

        self.assertEqual(owner_rows, sorted(OWNER_TODOS))
        self.assertEqual(reader_rows, sorted(READER_TODOS))
        self.assertNotEqual(owner_rows, reader_rows)

    # @feature permissions.chart-run-as-owner
    def test_a_chart_run_as_its_owner_applies_owner_permissions_without_switching_session_user(self):
        self.set_run_as_owner(1)

        with as_user(READER), db_connections():
            chart = frappe.get_doc(DT.CHART, self.chart.name)
            # the escalation must come from the declaration alone, never from
            # impersonating the owner for the rest of the request
            with patch.object(frappe, "set_user", side_effect=AssertionError("set_user in a request")):
                result = chart.fetch(force=True)

            self.assertEqual(frappe.session.user, READER)
            self.assertEqual(get_permission_user(), READER)

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))

    # @feature permissions.chart-run-as-owner query.script
    def test_a_script_reads_as_the_user_its_chart_runs_as(self):
        """`view.get_chart_data` on a chart over a script query. The script read
        as the session user, so a chart run as its owner ran it as the reader.
        Read without `force`, so a script's cached output is never the other one's.
        An admin writes the script (Q17); the owner makes the chart."""
        query = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": "Run As Owner Test Script",
                "workbook": self.workbook.name,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": "results = [{'description': frappe.session.user}]"}],
            }
        ).insert()
        with as_user(OWNER):
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Run As Owner Test Script Chart",
                    "workbook": self.workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": frappe.parse_json(self.chart.config),
                }
            ).insert()

        for run_as_owner, reads_as in ((1, OWNER), (0, READER)):
            with self.subTest(run_as_owner=run_as_owner):
                frappe.db.set_value(DT.CHART, chart.name, "run_as_owner", run_as_owner)
                with as_user(READER), db_connections():
                    result = get_chart_data(chart=chart.name)
                self.assertEqual(self.descriptions(result), [reads_as])
                self.assertEqual(frappe.session.user, "Administrator")

    # @feature permissions.chart-run-as-owner
    def test_the_builder_draws_the_rows_the_card_draws(self):
        """One chart, two surfaces. The builder read as the caller while the
        card read as the owner, so an author saw a number no reader ever does."""
        from insights.api.authoring import get_chart_data as authoring_chart_data

        self.set_run_as_owner(1)

        with as_user(READER), db_connections():
            built = authoring_chart_data(
                chart_type=self.chart.chart_type,
                query=self.query.name,
                config=frappe.parse_json(self.chart.config),
                chart_name=self.chart.name,
                force=True,
            )

        self.assertEqual(sorted(row["description"] for row in built["rows"]), sorted(OWNER_TODOS))

    # @feature permissions.run-as-owner-lapses
    def test_a_chart_whose_owner_may_no_longer_edit_it_runs_as_its_reader(self):
        """`view.get_chart_data` runs the card under `permission_user_for`, as the
        dashboard card, the drill and the builder do. The owner decides whose
        rows the chart serves only while they may edit it: disabled, or removed
        from the workbook, the chart runs as whoever reads it, as an alert
        whose enabler is stops."""
        with as_user(READER):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            update_share_permissions(workbook.name, [{"user": OWNER, "read": 1, "write": 1}])
        with as_user(OWNER):
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Run As Owner Lapse Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.copy_doc(self.chart)
            chart.update({"workbook": workbook.name, "query": query.name, "run_as_owner": 1})
            chart.insert()

        def rows():
            with as_user(READER), db_connections():
                return self.descriptions(get_chart_data(chart=chart.name, force=True))

        self.assertEqual(rows(), sorted(OWNER_TODOS))

        frappe.db.set_value("User", OWNER, "enabled", 0)
        self.addCleanup(frappe.db.set_value, "User", OWNER, "enabled", 1)
        self.assertEqual(rows(), sorted(READER_TODOS))
        frappe.db.set_value("User", OWNER, "enabled", 1)

        with as_user(READER):
            update_share_permissions(workbook.name, [])
        self.assertEqual(rows(), sorted(READER_TODOS))
        self.assertTrue(frappe.db.get_value(DT.CHART, chart.name, "run_as_owner"))

        # kept as a viewer, the owner reads the chart as everyone does: their
        # own rows, and all of them (`can_read_rows`, the drill's door)
        with as_user(READER):
            update_share_permissions(workbook.name, [{"user": OWNER, "read": 1, "write": 0}])
        self.assertEqual(rows(), sorted(READER_TODOS))
        self.assertTrue(can_read_rows(frappe.get_doc(DT.CHART, chart.name), OWNER))

    # @feature shared.rows-are-the-owners
    def test_a_guest_reads_a_public_chart_as_its_owner(self):
        """Guests have no permissions, so the widest level draws the owner's rows."""
        self.addCleanup(
            frappe.db.set_value,
            DT.CHART,
            self.chart.name,
            {"visibility": "Private", "run_as_owner": 0},
        )
        with as_user(OWNER):
            chart = frappe.get_doc(DT.CHART, self.chart.name)
            chart.visibility = "Public"
            chart.save()

        self.assertTrue(frappe.db.get_value(DT.CHART, self.chart.name, "run_as_owner"))
        self.assertEqual(self.descriptions(self.fetch_chart_data("Guest")), sorted(OWNER_TODOS))

    # @feature permissions.chart-run-as-owner permissions.request-body-not-trusted
    def test_request_payload_cannot_flip_the_declaration(self):
        """`permission_user.runs_as`, entered by `InsightsChartv3.fetch` and the
        drill. It reads the declaration off the stored document, so it holds
        even when handed a document built out of a request payload."""
        self.set_run_as_owner(0)

        forged = frappe.get_doc(DT.CHART, self.chart.name).as_dict()
        forged.update({"run_as_owner": 1, "owner": OWNER})

        with as_user(READER):
            self.assertEqual(permission_user_for(frappe.get_doc(forged)), READER)

    # @feature permissions.chart-run-as-owner permissions.request-body-not-trusted
    def test_a_chart_answers_its_rows_through_no_method_of_its_own(self):
        """`insights.api.run_doc_method`, which `resource.ts` calls for any
        whitelisted document method. The chart's own `get_data` took a page
        window off the wire, so a reader of a chart run as its owner paged past
        the `limit` the owner saved. `insights.api.view` is the reader's door."""
        self.set_run_as_owner(1)
        docs = frappe.as_json({"doctype": DT.CHART, "name": self.chart.name})

        for method in ("get_data", "fetch"):
            with as_user(READER), db_connections(), as_http_request():
                with self.assertRaises((AttributeError, frappe.PermissionError)):
                    insights_run_doc_method(method=method, docs=docs, args={"page": 2, "page_size": 10000})

    # @feature permissions.chart-run-as-owner permissions.site-user-permissions
    def test_non_site_db_rows_are_unfiltered_either_way(self):
        """External sources carry no Frappe permissions, so neither mode filters them."""
        table = ibis.memtable({"name": ["a", "b"], "value": [1, 2]})

        for user in (OWNER, READER):
            with self.subTest(user=user):
                self.assertIs(filter_rows_for(table, TEST_DS, "table1", user=user), table)

    # @feature permissions.team-grant permissions.table-row-restriction permissions.site-user-permissions permissions.card-says-it-is-scoped
    def test_a_reader_reads_the_site_rows_desk_or_a_team_grant_allows(self):
        """`view.get_chart_data` for the reader, on a chart that runs as them.
        On site data a team grant widens what desk allows and never narrows it,
        so the grant comes from an `Insights Team` as the Teams page writes it."""
        from insights.insights.doctype.insights_team.insights_team import clear_cache

        self.set_team_permissions(1)

        # no team grant at all: desk's own answer, the reader's assignments. A
        # role's match condition names nothing, so the card says nothing
        result = self.fetch_chart_data(READER)
        self.assertEqual(self.descriptions(result), sorted(READER_TODOS))
        self.assertNotIn("narrowed_by_permissions", result)

        team = self.grant_todos(READER, f"description == '{OWNER_TODOS[0]}'")

        # a restricted grant beside desk's own rows only adds to them, and a
        # grant that adds rows narrows nothing
        result = self.fetch_chart_data(READER)
        self.assertEqual(self.descriptions(result), sorted([*READER_TODOS, OWNER_TODOS[0]]))
        self.assertNotIn("narrowed_by_permissions", result)

        # where desk admits no row, the Table Restriction is what cuts the rows
        with patch(
            "insights.insights.doctype.insights_table_v3.insights_table_v3.desk_predicate",
            return_value=None,
        ):
            result = self.fetch_chart_data(READER)
        self.assertEqual(self.descriptions(result), [OWNER_TODOS[0]])
        self.assertTrue(result["narrowed_by_permissions"])

        team.team_permissions[0].table_restrictions = None
        team.save(ignore_permissions=True)
        clear_cache()

        # an unrestricted grant is the whole table, and nothing narrowed it
        result = self.fetch_chart_data(READER)
        self.assertEqual(self.descriptions(result), sorted([*READER_TODOS, *OWNER_TODOS]))
        self.assertNotIn("user_permissions", result)
        self.assertNotIn("narrowed_by_permissions", result)

    # @feature permissions.table-row-restriction permissions.card-says-it-is-scoped permissions.chart-run-as-owner
    def test_a_restriction_is_said_to_the_user_it_narrowed_and_no_one_else(self):
        """`authoring.get_chart_data` for the chart's writer, and
        `view.get_chart_data` for its reader once it runs as the owner. The
        owner's Table Restriction narrowed rows the reader is shown as the
        owner's, and is not a restriction the reader holds."""
        from insights.api.authoring import get_chart_data as get_authoring_data

        self.set_team_permissions(1)
        self.grant_todos(OWNER, f"description == '{READER_TODOS[0]}'")
        # desk admits no row, so the restriction cuts the rows (Q15)
        desk_admits_none = patch(
            "insights.insights.doctype.insights_table_v3.insights_table_v3.desk_predicate",
            return_value=None,
        )

        with desk_admits_none, as_user(OWNER), db_connections():
            authored = get_authoring_data(
                chart_type=self.chart.chart_type,
                query=self.query.name,
                config=frappe.parse_json(self.chart.config),
                chart_name=self.chart.name,
                force=True,
            )
        self.assertTrue(authored["narrowed_by_permissions"])

        self.set_run_as_owner(1)
        with desk_admits_none:
            self.assertTrue(self.fetch_chart_data(OWNER)["narrowed_by_permissions"])
            result = self.fetch_chart_data(READER)
        self.assertEqual(self.descriptions(result), [READER_TODOS[0]])
        self.assertNotIn("narrowed_by_permissions", result)

    # @feature permissions.team-grant permissions.table-row-restriction permissions.site-user-permissions
    def test_an_admin_reads_the_site_rows_desk_allows_whatever_their_team_grants(self):
        """`view.get_chart_data` for an Insights Admin, on a chart that runs as
        them. An admin passes the team gate everywhere, and that pass is no
        grant: on site data they read what desk gives them."""
        from insights.insights.doctype.insights_team.insights_team import clear_cache, is_admin

        self.set_team_permissions(1)
        frappe.get_doc(
            {
                "doctype": "Insights Team Member",
                "parent": "Admin",
                "parenttype": DT.TEAM,
                "parentfield": "team_members",
                "user": INSIGHTS_ADMIN,
            }
        ).db_insert()
        self.addCleanup(clear_cache)
        self.addCleanup(frappe.db.delete, "Insights Team Member", {"parent": "Admin", "user": INSIGHTS_ADMIN})
        clear_cache()
        self.assertTrue(is_admin(INSIGHTS_ADMIN))

        self.grant_todos(INSIGHTS_ADMIN, f"description == '{OWNER_TODOS[0]}'")

        self.assertEqual(self.descriptions(self.fetch_chart_data(INSIGHTS_ADMIN)), [])

    # @feature permissions.team-grant permissions.table-row-restriction permissions.site-user-permissions permissions.card-says-it-is-scoped
    def test_a_team_grant_hands_out_a_column_desk_hides_on_its_own_rows_only(self):
        """`view.get_chart_data` for the reader, on a chart drawing a column
        desk hides from them. A cell comes back if desk admits its row and its
        column, or a team grant admits its row: the column reads on the row the
        grant adds and is empty on the rows only desk admits, and the card says
        its permissions narrowed it."""
        self.set_team_permissions(1)
        self.grant_todos(READER, f"description == '{OWNER_TODOS[0]}'")
        self.make_status_permlevel()

        with as_user(OWNER):
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Run As Owner Test Statuses",
                    "workbook": self.workbook.name,
                    "query": self.query.name,
                    "chart_type": "Table",
                    "config": {
                        "rows": [
                            {"column_name": column, "dimension_name": column, "data_type": "String"}
                            for column in ("description", "status")
                        ],
                        "columns": [],
                        "values": [],
                        "order_by": [],
                    },
                }
            ).insert()
        self.addCleanup(frappe.delete_doc, DT.CHART, chart.name, force=True, ignore_permissions=True)

        with as_user(READER), db_connections():
            result = get_chart_data(chart=chart.name, force=True)

        self.assertEqual(
            {row["description"]: row["status"] for row in result["rows"]},
            {READER_TODOS[0]: None, OWNER_TODOS[0]: "Open"},
        )
        self.assertTrue(result["narrowed_by_permissions"])

        # a table desk opens whole to the reader: the grant narrows no row, and
        # the column it blanks is still said
        desk_admits_every_row = patch(
            "insights.insights.doctype.insights_table_v3.insights_table_v3.desk_predicate",
            return_value=True,
        )
        with desk_admits_every_row, as_user(READER), db_connections():
            result = get_chart_data(chart=chart.name, force=True)

        statuses = {row["description"]: row["status"] for row in result["rows"]}
        self.assertEqual(statuses[OWNER_TODOS[0]], "Open")
        self.assertIsNone(statuses[OWNER_TODOS[1]])
        self.assertTrue(result["narrowed_by_permissions"])

    # @feature permissions.card-says-it-is-scoped permissions.team-grant
    def test_a_blanked_column_marks_only_a_card_that_reads_it(self):
        """`view.get_chart_data`. The per-cell rule blanks `status` on the rows
        only desk admits. A card that never reads it draws a whole number and
        says nothing; one whose query filters by it says it was narrowed. A
        native SQL query is read by the columns it names."""
        self.blank_status()

        def native_chart(title, columns):
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": title,
                    "workbook": self.workbook.name,
                    "use_live_connection": 1,
                    "operations": [
                        {
                            "type": "sql",
                            "data_source": "Site DB",
                            "raw_sql": f"select {columns} from tabToDo where description like '{TODO_PREFIX}%'",
                        }
                    ],
                }
            ).insert()
            chart = frappe.copy_doc(self.chart)
            chart.update({"query": query.name, "title": title})
            return chart.insert().name

        with as_user(OWNER):
            native_plain = native_chart("Run As Owner Test Native", "description")
            native_status = native_chart("Run As Owner Test Native Status", "description, status")
            by_status = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Run As Owner Test Open",
                    "workbook": self.workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": [
                        *todo_operations(),
                        {
                            "type": "filter",
                            "column": {"type": "column", "column_name": "status"},
                            "operator": "=",
                            "value": "Open",
                        },
                    ],
                }
            ).insert()
            filtered = frappe.copy_doc(self.chart)
            filtered.update({"query": by_status.name, "title": "Run As Owner Test Open"})
            filtered.insert()

        with as_user(READER), db_connections():
            plain = get_chart_data(chart=self.chart.name, force=True)
            narrowed = get_chart_data(chart=filtered.name, force=True)
            native_plain = get_chart_data(chart=native_plain, force=True)
            native_status = get_chart_data(chart=native_status, force=True)

        self.assertEqual(self.descriptions(plain), sorted([*READER_TODOS, OWNER_TODOS[0]]))
        self.assertNotIn("narrowed_by_permissions", plain)
        self.assertTrue(narrowed["narrowed_by_permissions"])
        self.assertEqual(self.descriptions(native_plain), self.descriptions(plain))
        self.assertNotIn("narrowed_by_permissions", native_plain)
        self.assertTrue(native_status["narrowed_by_permissions"])

    # @feature permissions.card-says-it-is-scoped permissions.team-grant
    def test_the_table_browser_and_a_rows_level_mark_the_cells_they_draw_blanked(self):
        """`data_sources.get_data_source_table` for the table browser and
        `view.get_drill_data` for a drill's rows level. Both draw every column,
        so both draw `status` empty on the rows only desk admits, and say so
        as the card does."""
        from insights.api.data_sources import get_data_source_table
        from insights.api.view import get_drill_data

        self.blank_status()

        with as_user(READER), db_connections():
            browsed = get_data_source_table("Site DB", "tabToDo")
            rows = get_drill_data(
                chart=self.chart.name,
                drill_stack=[
                    {
                        "segment_filters": [
                            {"column": "description", "operator": "=", "value": READER_TODOS[0]}
                        ],
                        "action": {"rows": True},
                    }
                ],
            )

        self.assertIsNone(
            next(row for row in browsed["rows"] if row["description"] == READER_TODOS[0])["status"]
        )
        self.assertTrue(browsed["narrowed_by_permissions"])
        self.assertEqual([row["status"] for row in rows["rows"]], [None])
        self.assertTrue(rows["narrowed_by_permissions"])

    def blank_status(self):
        """A restricted grant for the reader and `status` hidden from them by
        desk: the per-cell rule blanks it on the rows only desk admits."""
        self.set_team_permissions(1)
        self.grant_todos(READER, f"description == '{OWNER_TODOS[0]}'")
        self.make_status_permlevel()

    def grant_todos(self, user, restriction=None):
        """A team of `user` granting `tabToDo`, as the Teams page writes it."""
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
        from insights.insights.doctype.insights_team.insights_team import clear_cache

        table = get_table_name("Site DB", "tabToDo")
        if not frappe.db.exists(DT.TABLE, table):
            frappe.get_doc(
                {"doctype": DT.TABLE, "table": "tabToDo", "label": "tabToDo", "data_source": "Site DB"}
            ).insert(ignore_permissions=True)

        team = frappe.get_doc(
            {"doctype": DT.TEAM, "team_name": f"Run As Owner Test Team {frappe.generate_hash(length=6)}"}
        )
        team.append("team_members", {"user": user})
        team.append(
            "team_permissions",
            {"resource_type": DT.TABLE, "resource_name": table, "table_restrictions": restriction},
        )
        team.insert(ignore_permissions=True)
        self.addCleanup(clear_cache)
        self.addCleanup(frappe.delete_doc, DT.TEAM, team.name, force=True, ignore_permissions=True)
        clear_cache()
        return team

    # @feature permissions.team-grant permissions.site-user-permissions
    def test_the_builder_lists_the_site_tables_desk_or_a_team_grant_allows(self):
        """`get_data_source_tables` fills the builder's table picker, so it lists
        what the read path reads: on site data desk admits a reader as a team
        grant does, and this reader is in no team."""
        from insights.api.data_sources import get_data_source_tables
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

        self.set_team_permissions(1)
        for table in ("tabToDo", "tabError Log"):
            if not frappe.db.exists(DT.TABLE, get_table_name("Site DB", table)):
                frappe.get_doc(
                    {"doctype": DT.TABLE, "table": table, "label": table, "data_source": "Site DB"}
                ).insert(ignore_permissions=True)

        def listed(search_term):
            with as_user(READER):
                tables = get_data_source_tables("Site DB", search_term=search_term)
            return [table.table_name for table in tables]

        self.assertIn("tabToDo", listed("tabToDo"))
        # desk refuses this one, and no team grants it
        self.assertNotIn("tabError Log", listed("tabError Log"))

    # @feature permissions.card-says-it-is-scoped
    def test_a_child_table_names_the_grants_frappe_cut_its_parent_by(self):
        """Frappe builds a child table's row filter from the parent's meta —
        `permission_doctype = parent_doctype or doctype`, and it never reads the
        child's own links. So a grant on a field only the parent links narrows
        the rows, and one on a field only the child links narrows nothing."""
        on_parent = self.grant(ADMIN, "Gender", "Male")
        self.grant(ADMIN, "Role", "System Manager")

        narrowed = user_permissions.narrowing("Has Role", ADMIN, parent_doctype="User")

        self.assertEqual(narrowed, {"Gender": [on_parent]})
        self.assertEqual(narrowed, user_permissions.narrowing("User", ADMIN))

    # @feature permissions.card-says-it-is-scoped
    def test_no_grant_is_named_where_frappe_cut_the_rows_by_sharing(self):
        """With no role that reads the doctype, frappe applies share conditions
        and no user permission at all. A card naming the grant would tell the
        reader a restriction they hold narrowed a number that sharing narrowed."""
        self.grant(READER, "Gender", "Male")

        self.assertEqual(user_permissions.narrowing("User", READER), {})

    def grant(self, user, doctype, document):
        """One User Permission, and the document it names."""
        permission = frappe.get_doc(
            {"doctype": "User Permission", "user": user, "allow": doctype, "for_value": document}
        ).insert(ignore_permissions=True)
        self.addCleanup(
            frappe.delete_doc, "User Permission", permission.name, force=True, ignore_permissions=True
        )
        return document
