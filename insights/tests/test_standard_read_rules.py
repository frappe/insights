"""A reader of standard content is filtered as a reader of any chart is.

On site data desk or a team grant admits them, whichever allows more, so a
shipped card is never refused to a desk user a team does not name.
"""

import frappe

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from insights.insights.doctype.insights_team.insights_team import clear_cache as clear_team_cache
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

SITE_DB = "Site DB"
TABLE = "tabToDo"
PREFIX = "Standard Read Rules Test"
WORKBOOK_TITLE = f"{PREFIX} Workbook"
TEAM = "standard-read-rules-team"

# a member of a team that was granted the table, under a row restriction
GRANTED = "standard-read-rules-granted@test.com"
# a reader in no team at all, which is every desk user on a site with teams
UNGRANTED = "standard-read-rules-ungranted@test.com"


def todo_operations():
    """A query over `tabToDo`, narrowed to this module's fixtures."""
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": SITE_DB, "table_name": TABLE},
        },
        {
            "type": "filter",
            "column": {"type": "column", "column_name": "description"},
            "operator": "contains",
            "value": PREFIX,
        },
    ]


class AStandardChartReadsAsAnyChart(InsightsIntegrationTestCase):
    """With team permissions on, the same chart in a site workbook and in a
    shipped one reads the same rows for a reader in a team and for one in none."""

    @classmethod
    def before_class(cls):
        cls.cleanup()
        create_user(GRANTED, first_name="Standard", last_name="Granted", roles="Insights User")
        create_user(UNGRANTED, first_name="Standard", last_name="Ungranted", roles="Insights User")

        # allocated to the reader, so frappe's own row permissions admit them and
        # what is left to observe is the team's half. Only the ungranted reader
        # holds a cancelled one, which the team's restriction admits
        cls.todos = [
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"{PREFIX} {status}",
                    "status": status,
                    "allocated_to": user,
                    "assigned_by": "Administrator",
                }
            )
            .insert(ignore_permissions=True)
            .name
            for user, statuses in (
                (GRANTED, ("Open", "Closed")),
                (UNGRANTED, ("Open", "Closed", "Cancelled")),
            )
            for status in statuses
        ]

        cls.table_row = get_table_name(SITE_DB, TABLE)
        if not frappe.db.exists(DT.TABLE, cls.table_row):
            frappe.get_doc(
                {
                    "doctype": DT.TABLE,
                    "table": TABLE,
                    "label": TABLE,
                    "data_source": SITE_DB,
                    "sync_mode": "Full",
                }
            ).insert(ignore_permissions=True)

        cls.enable_permissions_was = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 1)

        team = frappe.get_doc({"doctype": DT.TEAM, "team_name": TEAM})
        team.append("team_members", {"user": GRANTED})
        team.append("team_permissions", {"resource_type": DT.DATA_SOURCE, "resource_name": SITE_DB})
        team.append(
            "team_permissions",
            {
                "resource_type": DT.TABLE,
                "resource_name": cls.table_row,
                "table_restrictions": "status != 'Closed'",
            },
        )
        team.save(ignore_permissions=True)
        clear_team_cache()

        cls.plain, cls.shipped = cls.create_charts()

    @classmethod
    def after_class(cls):
        cls.cleanup()

    @classmethod
    def cleanup(cls):
        # first, because it is the one thing here that is not this module's own:
        # a teardown that throws below would otherwise leave the site's team
        # permissions on for every suite that runs after it
        if hasattr(cls, "enable_permissions_was"):
            frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.enable_permissions_was)

        # the fixture marks a workbook standard with a raw write, and a standard
        # workbook refuses every write outside developer mode - the delete
        # included - so the mark comes off the same way it went on
        for name in frappe.get_all(
            DT.WORKBOOK, filters={"title": ("like", f"{WORKBOOK_TITLE}%"), "is_standard": 1}, pluck="name"
        ):
            frappe.db.set_value(DT.WORKBOOK, name, "is_standard", 0)

        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for name in frappe.get_all("ToDo", filters={"description": ["like", f"%{PREFIX}%"]}, pluck="name"):
            frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)
        if frappe.db.exists(DT.TEAM, TEAM):
            frappe.delete_doc(DT.TEAM, TEAM, force=True, ignore_permissions=True)
        clear_team_cache()
        delete_users(GRANTED, UNGRANTED)

    @classmethod
    def create_charts(cls):
        """The same chart in two workbooks: one the site wrote, one an app ships."""
        names = []
        for title in (f"{PREFIX} Plain", f"{PREFIX} Shipped"):
            names.append(cls.create_chart(title))

        # the workbook is where "is this standard content" is answered, so the
        # mark goes on the workbook row the chart reads it off
        cls.shipped_workbook = frappe.db.get_value(DT.CHART, names[1], "workbook")
        frappe.db.set_value(DT.WORKBOOK, cls.shipped_workbook, "is_standard", 1)
        return names

    @classmethod
    def create_chart(cls, title):
        """A workbook holding one query over `tabToDo` and one table chart on it."""
        workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": f"{WORKBOOK_TITLE} {title}"}).insert()
        query = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": f"{title} Query",
                "workbook": workbook.name,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": todo_operations(),
            }
        ).insert()

        return (
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": title,
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": {
                        "rows": [
                            {
                                "column_name": "status",
                                "dimension_name": "status",
                                "data_type": "String",
                            }
                        ],
                        "columns": [],
                        "values": [],
                        "order_by": [],
                    },
                }
            )
            .insert()
            .name
        )

    def data_read_by(self, chart, user):
        with as_user(user), db_connections():
            return frappe.get_doc(DT.CHART, chart).fetch(force=True)

    def statuses_read_by(self, chart, user):
        rows = self.data_read_by(chart, user)["rows"]
        return sorted(row["status"] for row in rows)

    # @feature standard.read-rules permissions.site-user-permissions
    def test_a_reader_with_no_grant_reads_the_site_rows_desk_allows_them(self):
        """`view.get_chart_data` for a reader in no team: on site data desk
        admits them whether or not the chart is shipped."""
        self.assertEqual(self.statuses_read_by(self.plain, UNGRANTED), ["Cancelled", "Closed", "Open"])
        self.assertEqual(self.statuses_read_by(self.shipped, UNGRANTED), ["Cancelled", "Closed", "Open"])

    # @feature standard.read-rules permissions.team-grant
    def test_a_standard_chart_is_widened_by_a_teams_grant_as_any_chart_is(self):
        """`view.get_chart_data` for a reader in a team. The grant's restricted
        rows - the other reader's cancelled todo - join what desk allows them,
        whether or not the chart is shipped."""
        self.assertEqual(self.statuses_read_by(self.plain, GRANTED), ["Cancelled", "Closed", "Open"])
        self.assertEqual(self.statuses_read_by(self.shipped, GRANTED), ["Cancelled", "Closed", "Open"])
