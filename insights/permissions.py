# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Who may read or change Insights content, and on which grant.

Frappe asks this module two questions. `get_permission_query_conditions` names
the documents a list may show. `has_doc_permission` answers for one document.
Both run through `InsightsPermissions`, so a grant one seam honors the other
honors too.

The branching below is three eras layered - teams, then workbook sharing, then
declared visibility - but one rule holds under all of it: a grant is the union
of enumerable sources, per doctype and per action.

    Source                         Applies to                          Actions
    Admin (`is_admin`)             every permissioned doctype          all
    Ownership                      everything                          all
    DocShare                       workbook, dashboard, chart          per share flags
    Container inheritance          workbook -> items,                  follows container
                                   dashboard -> chart,
                                   chart -> query, query -> alert
    Team resource grant            source, table - and dashboard,      all
                                   chart (legacy)
    Team membership                team                                all
    Visibility                     dashboard, chart                    read only
    Preview key                    the previewed dashboard, its        read only
                                   charts, their queries
    Role (`check_app_permission`)  the authoring SPA, not documents    -

The table is exhaustive. A grant that is not in it does not exist. This file
decides every read of Insights content: the `is_public` column that published a
document before `visibility` is read by nothing but the patch that migrated it.

The rule the table is written for: a new grant source must earn a row here
before it earns a join in this file.

Four things the table does not say:

- A DocShare on content that declares visibility names a person. An org-wide
  one is not read there, because the `Everyone` level is the one mechanism that
  admits every signed-in user. A workbook declares no visibility, so its
  org-wide share is read.

- Actions fold. `has_doc_permission` is asked for read, share or write, and
  anything that is neither read nor share is asked as write. The list seam asks
  for read and nothing else.
- A document that does not exist yet has nothing to enumerate, so the controller
  admits it. The one exception is a new query, chart or dashboard that names a
  workbook, where the workbook's grant decides.
- Ownership is a source for every doctype on the document seam, but the list
  seam builds no owner branch for data sources and tables. Teams alone say which
  of those a list may show.
"""

from functools import cached_property

import frappe
import frappe.share
from pypika.terms import LiteralValue

from insights.insights.doctype.insights_team.insights_team import (
    get_teams,
    is_admin,
)

PERMISSION_DOCTYPES = [
    "Insights Data Source v3",
    "Insights Table v3",
    "Insights Team",
    "Insights Workbook",
    "Insights Query v3",
    "Insights Chart v3",
    "Insights Dashboard v3",
    "Insights Alert",
]

# if team permissions are not enabled,
# then these doctypes are accessible to all insights users
TEAM_BASED_PERMISSION_DOCTYPES = [
    "Insights Data Source v3",
    "Insights Table v3",
    "Insights Team",
    "Insights Dashboard v3",
    "Insights Chart v3",
]

INSIGHTS_ROLES = ("Insights User", "Insights Admin")

# content that declares its own visibility (`visibility` + `visible_to_roles`)
VISIBILITY_DOCTYPES = [
    "Insights Chart v3",
    "Insights Dashboard v3",
]

# The visibility levels, from the narrowest reach to the widest. The
# `visibility` field on chart and dashboard declares the same four options, and
# `test_visibility` asserts that this list and the schema agree.
PRIVATE = "Private"
ROLES = "Roles"
EVERYONE = "Everyone"
PUBLIC = "Public"
VISIBILITY_LEVELS = [PRIVATE, ROLES, EVERYONE, PUBLIC]

# levels that admit a reader without naming them
OPEN_LEVELS = [EVERYONE, PUBLIC]


def get_insights_users():
    """Everyone who may use Insights: an enabled holder of an Insights role.

    One definition serves both sides of sharing - the picker lists this set and
    `validate_shareable_users` accepts it - so a name the picker offers is never
    refused when the share is saved. Administrator is left out: it is nobody to
    browse for, though it can still own a workbook and be granted access to one.
    """
    from frappe.utils.user import get_users_with_role

    users = set()
    for role in INSIGHTS_ROLES:
        users.update(get_users_with_role(role))
    return users


class InsightsPermissions:
    def __init__(self, user=None):
        self.user = user or frappe.session.user
        self.user_teams = []
        if self.team_permissions_enabled:
            self.user_teams = get_teams(self.user)

    @cached_property
    def is_admin(self):
        return is_admin(self.user)

    @cached_property
    def team_permissions_enabled(self):
        return frappe.db.get_single_value("Insights Settings", "enable_permissions")

    @cached_property
    def user_roles(self):
        return frappe.get_roles(self.user)

    def get_permission_query_conditions(self, doctype: str) -> str:
        if doctype not in PERMISSION_DOCTYPES:
            return ""

        if self.is_admin:
            return ""

        if doctype == "Insights Team":
            if not self.user_teams:
                return "(`tabInsights Team`.name is NULL)"

            item_list = [frappe.db.escape(item) for item in self.user_teams]
            items_sql = ", ".join(item_list)
            return f"(`tabInsights Team`.name in ({items_sql}))"

        docs = self._build_permission_query(doctype, "read")
        if not docs:
            return ""

        return f"(`tab{doctype}`.name in ({docs}))"

    def has_doc_permission(self, doc, ptype):
        if doc.doctype not in PERMISSION_DOCTYPES:
            return True

        if self.is_admin:
            return True

        # imported here because `insights.api` reaches back into this module
        from insights.api.shared import is_being_previewed

        # A preview render arrives as Guest carrying a key cut for one dashboard,
        # so the key is its whole grant. It reaches the documents the image it
        # produces already shows and stops there. The grant lives here rather
        # than on one endpoint because the render reads through the same
        # endpoints every other reader does.
        if ptype == "read" and is_being_previewed(doc.doctype, doc.name):
            return True

        is_new = not doc.name or doc.is_new()
        if is_new and doc.doctype in ["Insights Data Source v3", "Insights Table v3"]:
            # let further permission checks handle it
            return True

        if doc.doctype == "Insights Team":
            return doc.name in self.user_teams

        is_owner = doc.owner == self.user
        access_type = "write" if ptype not in ["read", "share"] else ptype

        if is_new and hasattr(doc, "workbook") and doc.workbook:
            # when creating a new query/chart/dashboard
            # if it is linked to a workbook, check if user has access to the workbook
            docs = self._build_permission_query("Insights Workbook", access_type)
            return (
                docs.where(frappe.qb.DocType("Insights Workbook").name == doc.workbook)
                .limit(1)
                .run(pluck="name")
            )

        if is_new or is_owner:
            return True

        docs = self._build_permission_query(doc.doctype, access_type)
        return docs.where(frappe.qb.DocType(doc.doctype).name == doc.name).limit(1).run(pluck="name")

    def _build_permission_query(self, doctype, ptype):
        """Returns a query to get docs with `ptype`  permission"""
        query = None
        if doctype == "Insights Data Source v3":
            query = self._build_source_permission_query(ptype)
        if doctype == "Insights Table v3":
            query = self._build_table_permission_query(ptype)
        if doctype == "Insights Workbook":
            query = self._build_workbook_permission_query(ptype)
        if doctype == "Insights Dashboard v3":
            query = self._build_dashboard_permission_query(ptype)
        if doctype == "Insights Chart v3":
            query = self._build_chart_permission_query(ptype)
        if doctype == "Insights Query v3":
            query = self._build_query_permission_query(ptype)
        if doctype == "Insights Alert":
            query = self._build_alert_permission_query(ptype)
        return query

    def _build_visibility_query(self, doctype, ptype):
        """Returns a query to get docs whose declared visibility admits this user.

        Declared visibility is one grant source beside owner, DocShare and
        the workbook/dashboard links. It is view-only: no level ever grants
        write or share, and no level consults the `Insights User` role.
        """
        if ptype != "read" or doctype not in VISIBILITY_DOCTYPES:
            return None

        Content = frappe.qb.DocType(doctype)

        if self.user == "Guest":
            # the levels are strict, so a guest only ever reaches the widest
            return frappe.qb.from_(Content).select(Content.name).where(Content.visibility == PUBLIC)

        query = frappe.qb.from_(Content).select(Content.name)
        admits_user = Content.visibility.isin(OPEN_LEVELS)

        roles = [role for role in self.user_roles if role != "Guest"]
        if roles:
            HasRole = frappe.qb.DocType("Has Role")
            NamedRoles = (
                frappe.qb.from_(HasRole)
                .select(HasRole.parent.as_("name"))
                .where(
                    (HasRole.parenttype == doctype)
                    & (HasRole.parentfield == "visible_to_roles")
                    & (HasRole.role.isin(roles))
                )
            )
            query = query.left_join(NamedRoles).on(Content.name == NamedRoles.name)
            admits_user = admits_user | ((Content.visibility == ROLES) & NamedRoles.name.isnotnull())

        return query.where(admits_user)

    def _with_visibility_grant(self, query, Content, doctype, ptype, granted):
        """Adds declared visibility to a doctype's grant sources"""
        visible = self._build_visibility_query(doctype, ptype)
        if visible is None:
            return query.where(granted)

        return (
            query.left_join(visible)
            .on(Content.name == visible.name)
            .where(granted | visible.name.isnotnull())
        )

    def _build_source_permission_query(self, ptype):
        # if team permissions are not enabled, all data sources are accessible
        if not self.team_permissions_enabled:
            return frappe.qb.from_(frappe.qb.DocType("Insights Data Source v3")).select("name")

        # if team permissions are enabled, allow data sources of allowed tables
        DataSource = frappe.qb.DocType("Insights Data Source v3")
        Table = frappe.qb.DocType("Insights Table v3")
        AllowedTables = self._build_table_permission_query(ptype)

        return (
            frappe.qb.from_(DataSource)
            .select(DataSource.name)
            .left_join(Table)
            .on(Table.data_source == DataSource.name)
            .left_join(AllowedTables)
            .on(Table.name == AllowedTables.name)
            .where(AllowedTables.name.isnotnull())
            .distinct()
        )

    def _build_table_permission_query(self, ptype):
        # if team permissions are not enabled, all tables are accessible
        if not self.team_permissions_enabled:
            return frappe.qb.from_(frappe.qb.DocType("Insights Table v3")).select("name")

        # if team permissions are enabled,
        # tables linked to user's teams are accessible
        # & all tables of data sources linked to user's teams
        AllowedTables = self._build_resource_query("Insights Table v3")

        Table = frappe.qb.DocType("Insights Table v3")
        AllowedSources = self._build_resource_query("Insights Data Source v3")
        TablesOfAllowedSources = (
            frappe.qb.from_(Table)
            .select(Table.name.as_("name"))
            .left_join(AllowedSources)
            .on(Table.data_source == AllowedSources.name)
            .where(AllowedSources.name.isnotnull())
        )

        return (
            frappe.qb.from_(Table)
            .select(Table.name)
            .left_join(AllowedTables)
            .on(Table.name == AllowedTables.name)
            .left_join(TablesOfAllowedSources)
            .on(Table.name == TablesOfAllowedSources.name)
            .where(AllowedTables.name.isnotnull() | TablesOfAllowedSources.name.isnotnull())
        )

    def _build_workbook_permission_query(self, ptype):
        DocShare = frappe.qb.DocType("DocShare")
        Workbook = frappe.qb.DocType("Insights Workbook")

        OwnedWorkbooks = frappe.qb.from_(Workbook).select(Workbook.name).where(Workbook.owner == self.user)

        SharedWorkbooks = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Workbook")
                & (DocShare[ptype] == 1)
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
            )
        )

        return (
            frappe.qb.from_(Workbook)
            .select(Workbook.name)
            .left_join(OwnedWorkbooks)
            .on(Workbook.name == OwnedWorkbooks.name)
            .left_join(SharedWorkbooks)
            .on(Workbook.name == SharedWorkbooks.share_name)
            .where(OwnedWorkbooks.name.isnotnull() | SharedWorkbooks.share_name.isnotnull())
        )

    def _build_dashboard_permission_query(self, ptype):
        Dashboard = frappe.qb.DocType("Insights Dashboard v3")
        OwnedDashboards = (
            frappe.qb.from_(Dashboard).select(Dashboard.name).where(Dashboard.owner == self.user)
        )

        DocShare = frappe.qb.DocType("DocShare")
        SharedDashboards = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Dashboard v3")
                & (DocShare[ptype] == 1)
                & (DocShare.user == self.user)
            )
        )

        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .left_join(AllowedWorkbooks)
            .on(Dashboard.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        AllowedDashboards = self._build_resource_query("Insights Dashboard v3")

        query = (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .left_join(OwnedDashboards)
            .on(Dashboard.name == OwnedDashboards.name)
            .left_join(SharedDashboards)
            .on(Dashboard.name == SharedDashboards.share_name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Dashboard.name == LinkedWithAllowedWorkbooks.name)
            .left_join(AllowedDashboards)
            .on(Dashboard.name == AllowedDashboards.name)
        )
        granted = (
            OwnedDashboards.name.isnotnull()
            | SharedDashboards.share_name.isnotnull()
            | LinkedWithAllowedWorkbooks.name.isnotnull()
            | AllowedDashboards.name.isnotnull()
        )

        return self._with_visibility_grant(query, Dashboard, "Insights Dashboard v3", ptype, granted)

    def _build_chart_permission_query(self, ptype):
        DocShare = frappe.qb.DocType("DocShare")
        Chart = frappe.qb.DocType("Insights Chart v3")
        DashboardChart = frappe.qb.DocType("Insights Dashboard Chart v3")

        OwnedCharts = frappe.qb.from_(Chart).select(Chart.name).where(Chart.owner == self.user)

        SharedCharts = (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where(
                (DocShare.share_doctype == "Insights Chart v3")
                & (DocShare[ptype] == 1)
                & (DocShare.user == self.user)
            )
        )

        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(AllowedWorkbooks)
            .on(Chart.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        AllowedDashboards = self._build_dashboard_permission_query(ptype)

        LinkedWithAllowedDashboards = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(DashboardChart)
            .on(Chart.name == DashboardChart.chart)
            .left_join(AllowedDashboards)
            .on(DashboardChart.parent == AllowedDashboards.name)
            .where(AllowedDashboards.name.isnotnull())
        )

        AllowedCharts = self._build_resource_query("Insights Chart v3")

        query = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(OwnedCharts)
            .on(Chart.name == OwnedCharts.name)
            .left_join(SharedCharts)
            .on(Chart.name == SharedCharts.share_name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Chart.name == LinkedWithAllowedWorkbooks.name)
            .left_join(LinkedWithAllowedDashboards)
            .on(Chart.name == LinkedWithAllowedDashboards.name)
            .left_join(AllowedCharts)
            .on(Chart.name == AllowedCharts.name)
        )
        granted = (
            OwnedCharts.name.isnotnull()
            | SharedCharts.share_name.isnotnull()
            | LinkedWithAllowedWorkbooks.name.isnotnull()
            # a chart on a dashboard inherits the dashboard's visibility,
            # downward only - see _build_dashboard_permission_query
            | LinkedWithAllowedDashboards.name.isnotnull()
            | AllowedCharts.name.isnotnull()
        )

        return self._with_visibility_grant(query, Chart, "Insights Chart v3", ptype, granted)

    def _build_query_permission_query(self, ptype):
        Query = frappe.qb.DocType("Insights Query v3")

        OwnedQueries = frappe.qb.from_(Query).select(Query.name).where(Query.owner == self.user)

        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(AllowedWorkbooks)
            .on(Query.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        Chart = frappe.qb.DocType("Insights Chart v3")
        AllowedCharts = self._build_chart_permission_query(ptype)
        AllowedCharts = AllowedCharts.select(Chart.query)

        LinkedWithAllowedCharts = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(AllowedCharts)
            .on(Query.name == AllowedCharts.query)
            .where(AllowedCharts.name.isnotnull())
        )

        return (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(OwnedQueries)
            .on(Query.name == OwnedQueries.name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Query.name == LinkedWithAllowedWorkbooks.name)
            .left_join(LinkedWithAllowedCharts)
            .on(Query.name == LinkedWithAllowedCharts.name)
            .where(
                OwnedQueries.name.isnotnull()
                | LinkedWithAllowedWorkbooks.name.isnotnull()
                | LinkedWithAllowedCharts.name.isnotnull()
            )
        )

    def _build_alert_permission_query(self, ptype):
        Alert = frappe.qb.DocType("Insights Alert")

        OwnedAlerts = frappe.qb.from_(Alert).select(Alert.name).where(Alert.owner == self.user)

        QueryWithWriteAccess = self._build_query_permission_query(ptype)

        LinkedWithQueryWithWriteAccess = (
            frappe.qb.from_(Alert)
            .select(Alert.name)
            .left_join(QueryWithWriteAccess)
            .on(Alert.query == QueryWithWriteAccess.name)
            .where(QueryWithWriteAccess.name.isnotnull())
        )

        return (
            frappe.qb.from_(Alert)
            .select(Alert.name)
            .left_join(OwnedAlerts)
            .on(Alert.name == OwnedAlerts.name)
            .left_join(LinkedWithQueryWithWriteAccess)
            .on(Alert.name == LinkedWithQueryWithWriteAccess.name)
            .where(OwnedAlerts.name.isnotnull() | LinkedWithQueryWithWriteAccess.name.isnotnull())
        )

    def _build_resource_query(self, doctype):
        """Grants on `doctype` that the user holds through a team.

        A team is the only thing that carries a grant, so a user in no team must
        match no row. That case cannot be written as a test of a column: `parent`
        links a grant back to its team and is set on every row, so any predicate
        over it is true for all of them. `isin([])` is not an option either -
        pypika renders it as the invalid `IN ()`. State the empty set as a false
        constant, where it cannot be read as its own opposite.
        """
        Resource = frappe.qb.DocType("Insights Resource Permission")

        held_by_a_team_of_the_user = (
            Resource.parent.isin(self.user_teams) if self.user_teams else LiteralValue("1 = 0")
        )
        condition = (
            (Resource.resource_type == doctype)
            & Resource.resource_name.isnotnull()
            & held_by_a_team_of_the_user
        )

        return frappe.qb.from_(Resource).select(Resource.resource_name.as_("name")).where(condition)


def check_referenced_query_access(query_name):
    """A query named by another document is still a document you have to read.

    A reference resolves to the whole query - its operations, its native SQL and
    the tables it reads - and the compiled result brings all of it back.

    An unattended execution has no caller to check, so it is checked against the
    user it runs as - the one recorded when the content was published.
    """
    from insights.permission_user import get_permission_user

    # a name with no row resolves to nothing. The build says "not found" instead.
    if not frappe.db.exists("Insights Query v3", query_name):
        return

    if not frappe.has_permission(
        "Insights Query v3", ptype="read", doc=query_name, user=get_permission_user()
    ):
        frappe.throw(
            frappe._("You do not have access to a query this one references"),
            frappe.PermissionError,
        )


def check_chart_query_access(chart):
    """A chart may only point at a query its owner can read.

    The link is a grant, not a reference: `_build_query_permission_query` gives
    read on every query linked from a chart the caller can read. So the link has
    to be checked where it is written, or it widens the owner's own access.

    Only a changed link is checked. An existing chart stays saveable by anyone
    who may already read it, whose access to the query runs through this link.
    """
    if not chart.query or not chart.has_value_changed("query"):
        return

    if not frappe.has_permission("Insights Query v3", ptype="read", doc=chart.query):
        frappe.throw(
            frappe._("You do not have access to the query this chart is built on"),
            frappe.PermissionError,
        )


def validate_visibility(doc):
    """Widening a document's visibility is a share, not a write.

    `visibility` is an ordinary field, so the generic write surface reaches it.
    Widening it hands the owner's own read access to people who hold none of
    their own - a guest on the open internet, at the widest level - and that is
    what `share` means. So the level is checked where it is written, the same way
    a chart's query link is.

    Only a widening move is checked. Narrowing takes nothing away from anybody,
    and a level that did not move leaves the document as saveable as the rest of
    it.
    """
    if not doc.has_value_changed("visibility"):
        return

    before = doc.get_doc_before_save()
    if visibility_level(doc.visibility) <= visibility_level(before.visibility if before else None):
        return

    if not frappe.has_permission(doc.doctype, ptype="share", doc=doc if doc.is_new() else doc.name):
        frappe.throw(
            frappe._("You do not have permission to change who can see this"),
            frappe.PermissionError,
        )

    if doc.visibility in OPEN_LEVELS:
        from insights.telemetry import capture_share_granted

        shared = "chart" if doc.doctype == "Insights Chart v3" else "dashboard"
        capture_share_granted(shared, "public" if doc.visibility == PUBLIC else "org", 1)


def validate_public_permissions(chart):
    """The Public level means the owner's rows.

    Guests have no permissions of their own, so a chart that applies each user's
    draws an empty page for the very reader a public link is for. That is never
    what an owner meant, so reaching the widest level unchecks the box.

    Unchecking it on the way up and refusing it afterwards is what keeps the read
    path free of a Guest branch: `permission_user_for` reads a stored declaration
    that can no longer be checked at this level. Coming back down leaves the box
    where the move put it - the owner may change it from the chart's share dialog.

    A chart reaches a guest at its own level or through a Public dashboard it is
    linked to, and `update_linked_charts_permissions` unchecks the box only on the
    dashboard's save. So the chart's own save asks the inverse question, or the
    next save of a linked chart would hand the guest an empty page again.
    """
    if chart.visibility == PUBLIC and chart.has_value_changed("visibility"):
        chart.apply_user_permissions = 0

    if not chart.apply_user_permissions:
        return

    if chart.visibility == PUBLIC:
        frappe.throw(
            frappe._("A public chart runs with its owner's permissions, so it cannot apply each user's."),
            frappe.ValidationError,
        )

    public_dashboard = public_dashboards_linking(chart)
    if public_dashboard:
        frappe.throw(
            frappe._(
                "This chart is on the public dashboard {0}, so it runs with its owner's permissions and cannot apply each user's."
            ).format(public_dashboard),
            frappe.ValidationError,
        )


def public_dashboards_linking(chart) -> str | None:
    """The title of a Public dashboard this chart is linked to, if there is one."""
    if chart.is_new():
        return None

    Dashboard = frappe.qb.DocType("Insights Dashboard v3")
    DashboardChart = frappe.qb.DocType("Insights Dashboard Chart v3")

    dashboards = (
        frappe.qb.from_(DashboardChart)
        .join(Dashboard)
        .on(Dashboard.name == DashboardChart.parent)
        .select(Dashboard.title)
        .where(
            (DashboardChart.parenttype == "Insights Dashboard v3")
            & (DashboardChart.chart == chart.name)
            & (Dashboard.visibility == PUBLIC)
        )
        .limit(1)
        .run(pluck=True)
    )

    return dashboards[0] if dashboards else None


def update_linked_charts_permissions(dashboard):
    """The same rule for the charts a Public dashboard is linked to.

    `_build_chart_permission_query` hands a guest read on every chart placed on
    a Public dashboard without touching the charts' own level, so the dashboard
    is where their permissions have to be settled.
    """
    if dashboard.visibility != PUBLIC or not dashboard.has_value_changed("visibility"):
        return

    for row in dashboard.linked_charts:
        frappe.db.set_value("Insights Chart v3", row.chart, "apply_user_permissions", 0)


def visibility_level(visibility: str | None) -> int:
    """How far a declared visibility reaches.

    A visibility the field does not name reaches nobody, because every level is
    matched by its exact name. So it sits at the bottom beside `Private`.
    """
    return VISIBILITY_LEVELS.index(visibility) if visibility in VISIBILITY_LEVELS else 0


def check_dashboard_chart_access(dashboard):
    """The same rule one level up.

    `_build_chart_permission_query` grants read on every chart placed on a
    dashboard the caller can read, so naming a chart here is the same kind of
    grant.
    """
    for row in dashboard.linked_charts:
        if not frappe.has_permission("Insights Chart v3", ptype="read", doc=row.chart):
            frappe.throw(
                frappe._("You do not have access to one of the charts on this dashboard"),
                frappe.PermissionError,
            )


def has_doc_permission(doc, ptype, user):
    return InsightsPermissions(user).has_doc_permission(doc, ptype)


def get_permission_query_conditions(user, doctype):
    return InsightsPermissions(user).get_permission_query_conditions(doctype)


def check_app_permission():
    """The authoring gate: may this person enter the builder?

    It answers for the app, not for a document, and it is never consulted for
    viewing. `visibility` decides who reads a dashboard, and a view of it mounts
    for people who hold no Insights role at all. Editing is both questions at
    once - write rights on the document AND a role - and `can_write` in
    `api/view.py` is the one place that conjunction is made.
    """
    if frappe.session.user == "Administrator":
        return True

    roles = frappe.get_roles()
    if any(role in ["Insights User", "Insights Admin"] for role in roles):
        return True

    return False
