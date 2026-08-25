"""A query reached through a reference is read like any other query.

An operation may source, join or union another query, and a dashboard filter may
link one. Either way the reference resolves to the whole query - its operations,
its native SQL, and the tables it reads - and the compiled result carries all of
it back. So the rule is the same as reading the query directly.
"""

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    as_user,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import USER_1, USER_2, create_test_users

OWNER = USER_1
OTHER = USER_2

SECRET = "referenced query secret"
SOURCE_ROWS = f"results = [{{'secret': '{SECRET}', 'amount': 1}}]"


def create_source_query(owner, workbook, title):
    """A query that stands on its own, so no table permission enters the picture."""
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 0,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": SOURCE_ROWS}],
            }
        ).insert()


def create_referencing_query(owner, workbook, referenced, title):
    with as_user(owner):
        return frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": title,
                "workbook": workbook,
                "use_live_connection": 0,
                "is_builder_query": 1,
                "operations": [
                    {
                        "type": "source",
                        "table": {"type": "query", "query_name": referenced},
                    }
                ],
            }
        ).insert()


class ReferencedQueryIsReadChecked:
    """The rules. Both `enable_permissions` settings run them.

    The setting scopes data sources and tables to teams. These queries carry no
    table, so what is left is the reference itself.
    """

    ENABLE_PERMISSIONS = 0

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.owner_workbook = create_test_workbook(OWNER, title="Reference Owner Workbook").name
        cls.owner_query = create_source_query(OWNER, cls.owner_workbook, "Reference Owner Source").name
        cls.owner_reference = create_referencing_query(
            OWNER, cls.owner_workbook, cls.owner_query, "Reference Owner Consumer"
        ).name

        cls.other_workbook = create_test_workbook(OTHER, title="Reference Other Workbook").name
        cls.other_reference = create_referencing_query(
            OTHER, cls.other_workbook, cls.owner_query, "Reference Other Consumer"
        ).name

    @classmethod
    def after_class(cls):
        for name in (cls.owner_workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)

    def execute(self, name):
        with db_connections():
            return frappe.get_doc(DT.QUERY, name).execute()

    def test_the_owner_cannot_be_read_by_the_other_user(self):
        """The baseline the refusals below are measured against."""
        with self.as_user(OTHER):
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=self.owner_query))

    def test_a_query_reference_resolves_for_someone_who_may_read_it(self):
        with self.as_user(OWNER):
            result = self.execute(self.owner_reference)
        self.assertEqual(result["rows"][0]["secret"], SECRET)

    def test_a_query_reference_is_refused_to_someone_who_may_not(self):
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            self.execute(self.other_reference)

    def test_a_refused_reference_returns_no_sql(self):
        """The compiled SQL is the query's logic, so a refusal returns none of it."""
        with self.as_user(OTHER):
            try:
                result = self.execute(self.other_reference)
            except frappe.PermissionError:
                return
            self.fail(f"the reference resolved and returned {result.get('sql')}")

    def test_a_reference_sent_inline_is_refused_too(self):
        """The operations arrive in the request, so the reference need not be saved."""
        with self.as_user(OTHER):
            doc = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "name": "new-query-inline",
                    "workbook": self.other_workbook,
                    "use_live_connection": 0,
                    "is_builder_query": 1,
                    "__islocal": True,
                    "operations": [
                        {
                            "type": "source",
                            "table": {"type": "query", "query_name": self.owner_query},
                        }
                    ],
                }
            )
            with self.assertRaises(frappe.PermissionError), db_connections():
                doc.execute()


class DashboardFilterReadsTheQuery:
    """The same rule where a dashboard filter names a query.

    A filter links a column as `` `<query>`.`<column>` ``. The dashboard says
    which columns it filters on, so it cannot also be what says which queries the
    caller may reach.
    """

    ENABLE_PERMISSIONS = 0

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.owner_workbook = create_test_workbook(OWNER, title="Filter Owner Workbook").name
        cls.owner_query = create_source_query(OWNER, cls.owner_workbook, "Filter Owner Source").name

        cls.other_workbook = create_test_workbook(OTHER, title="Filter Other Workbook").name
        cls.other_query = create_source_query(OTHER, cls.other_workbook, "Filter Other Source").name

        cls.owner_dashboard = cls.create_dashboard(OWNER, cls.owner_workbook, cls.owner_query)
        cls.other_dashboard = cls.create_dashboard(OTHER, cls.other_workbook, cls.owner_query)

    @classmethod
    def create_dashboard(cls, owner, workbook, query):
        with as_user(owner):
            return (
                frappe.get_doc(
                    {
                        "doctype": DT.DASHBOARD,
                        "title": f"Filter Dashboard {workbook}",
                        "workbook": workbook,
                        "items": [
                            {
                                "id": "filter-1",
                                "type": "filter",
                                "links": {"chart-1": f"`{query}`.`secret`"},
                            }
                        ],
                    }
                )
                .insert()
                .name
            )

    @classmethod
    def after_class(cls):
        for name in (cls.owner_workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)

    def distinct_values(self, dashboard, query):
        with db_connections():
            return frappe.get_doc(DT.DASHBOARD, dashboard).get_distinct_column_values(query, "secret")

    def test_a_filter_reads_a_query_its_owner_may_read(self):
        with self.as_user(OWNER):
            values = self.distinct_values(self.owner_dashboard, self.owner_query)
        self.assertEqual(values, [SECRET])

    def test_a_filter_cannot_read_a_query_its_owner_may_not(self):
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            self.distinct_values(self.other_dashboard, self.owner_query)


class TestReferencedQueryIsReadChecked(ReferencedQueryIsReadChecked, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestReferencedQueryIsReadCheckedWithTeamPermissions(
    ReferencedQueryIsReadChecked, InsightsIntegrationTestCase
):
    ENABLE_PERMISSIONS = 1


class TestDashboardFilterReadsTheQuery(DashboardFilterReadsTheQuery, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestDashboardFilterReadsTheQueryWithTeamPermissions(
    DashboardFilterReadsTheQuery, InsightsIntegrationTestCase
):
    ENABLE_PERMISSIONS = 1
