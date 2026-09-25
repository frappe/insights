"""Standard content filters rows for its reader like any other chart.

On site data, a reader gets the rows that desk permissions or a team grant
allow, whichever allows more. So a desk user in no team can still read a
standard chart.
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

# in a team granted the table with a row restriction
GRANTED = "standard-read-rules-granted@test.com"
# in no team, like most desk users on a site with teams
UNGRANTED = "standard-read-rules-ungranted@test.com"


def todo_operations():
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
    """With team permissions on, a chart reads the same rows in a site workbook
    and in a standard one, for a reader in a team and for one in none."""

    @classmethod
    def before_class(cls):
        cls.cleanup()
        create_user(GRANTED, first_name="Standard", last_name="Granted", roles="Insights User")
        create_user(UNGRANTED, first_name="Standard", last_name="Ungranted", roles="Insights User")

        # each ToDo is allocated to its reader, so desk permissions admit the
        # reader and the tests observe only the team grant. Only the ungranted
        # reader has a cancelled ToDo, and the team's restriction admits it
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
        # restore this site setting first. If a later step throws, team
        # permissions would stay on for every suite that runs after this one
        if hasattr(cls, "enable_permissions_was"):
            frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.enable_permissions_was)

        # outside developer mode a standard workbook refuses every write,
        # including delete. The fixture set the mark with a raw write, so remove
        # it the same way
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
        names = []
        for title in (f"{PREFIX} Plain", f"{PREFIX} Shipped"):
            names.append(cls.create_chart(title))

        # a chart is standard when its workbook is, so mark the workbook
        cls.shipped_workbook = frappe.db.get_value(DT.CHART, names[1], "workbook")
        frappe.db.set_value(DT.WORKBOOK, cls.shipped_workbook, "is_standard", 1)
        return names

    @classmethod
    def create_chart(cls, title):
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
        """Protects `view.get_chart_data` for a reader in no team. Desk
        permissions admit them whether or not the chart is standard."""
        self.assertEqual(self.statuses_read_by(self.plain, UNGRANTED), ["Cancelled", "Closed", "Open"])
        self.assertEqual(self.statuses_read_by(self.shipped, UNGRANTED), ["Cancelled", "Closed", "Open"])

    # @feature standard.read-rules permissions.team-grant
    def test_a_standard_chart_is_widened_by_a_teams_grant_as_any_chart_is(self):
        """Protects `view.get_chart_data` for a reader in a team. The grant's
        rows, here the other reader's cancelled ToDo, add to what desk allows,
        whether or not the chart is standard."""
        self.assertEqual(self.statuses_read_by(self.plain, GRANTED), ["Cancelled", "Closed", "Open"])
        self.assertEqual(self.statuses_read_by(self.shipped, GRANTED), ["Cancelled", "Closed", "Open"])
