# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Who may read or change Insights content, and on which grant.

Frappe asks this module two questions. `get_permission_query_conditions` names
the documents a list may show. `has_doc_permission` answers for one document.
Both run through `InsightsPermissions`, so a grant one seam honors the other
honors too.

The branching below is three eras layered — teams, then workbook sharing, then
the visibility ladder — but one rule holds under all of it: a grant is the union
of enumerable sources, per doctype and per action.

Two grants enumerate nothing. They answer for the whole controller and return,
so they stand above the union as bypasses:

    Bypass                           Applies to                  Actions
    Admin (`is_admin`)               every permissioned doctype  all
    Preview key (`has_preview_key`)  every permissioned doctype  read only

The rest are sources. Each one names documents, and a doctype's grant is what
its sources add up to:

    Source                         Applies to                          Actions
    Ownership                      everything                          all
    DocShare                       workbook, dashboard, chart          per share flags
    Container inheritance          workbook -> items,                  follows container
                                   dashboard -> chart,
                                   chart -> query, query -> alert
    Team resource grant            source, table — and dashboard,      all
                                   chart (legacy)
    Team membership                team                                all
    Audience ladder                dashboard, chart                    read only
    Seat (`check_app_permission`)  the authoring SPA, not documents    —

The table is exhaustive: a grant that is not in it does not exist. That closed
only recently. `3c0d5edb` retired the `is_public` walk and `api/shared.py`, the
second read path, so every read of Insights content is now decided here. The
`is_public` column stays on the content doctypes, with nothing reading it.

The rule the table is written for: a new grant source must earn a row here
before it earns a join in this file.

Four things the table does not say:

- Actions fold. `has_doc_permission` is asked for read, share or write, and
  anything that is neither read nor share is asked as write. The list seam asks
  for read and nothing else.
- Two of the rows answer to a site setting. With `enable_permissions` off, data
  sources and tables are open to every Insights user and no membership is read
  at all, which empties the team resource grant and the team membership rows
  both — a non-admin sees no team while the setting is off. With it on, a team
  grant reaches the members of the granting team and nobody else, so a user who
  belongs to no team draws nothing from either row.
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

# content that carries a visibility ladder (`visibility` + `visible_to_roles`)
VISIBILITY_LADDER_DOCTYPES = [
    "Insights Chart v3",
    "Insights Dashboard v3",
]

# rungs that admit a viewer without naming them
OPEN_AUDIENCES = ["Everyone", "Public"]

# what the browser that takes a dashboard's preview image carries
PREVIEW_KEY_HEADER = "X-Insights-Preview-Key"


def has_valid_preview_key():
    """Whether this request is the site taking a picture of its own page.

    The dashboard controller mints the key, renders the page in a headless
    browser and drops the key again, so it is alive for the length of one shot
    and nobody outside the server ever sees it. It is a read grant and nothing
    more: the request reads the page as a viewer would, and writes nothing.
    """
    if not frappe.request:
        return False

    key = frappe.request.headers.get(PREVIEW_KEY_HEADER)
    return bool(key) and bool(frappe.cache.get_value(f"insights_preview_key:{key}"))


class InsightsPermissions:
    def __init__(self, user=None):
        self.user = user or frappe.session.user
        # the teams whose grants this user carries. Empty when the user belongs
        # to no team, and empty when team permissions are off site-wide: both
        # mean the same thing to every reader below, which is no team grant.
        self.user_teams = []
        if self.team_permissions_enabled:
            self.user_teams = get_teams(self.user)

    @cached_property
    def is_admin(self):
        return is_admin(self.user)

    @cached_property
    def has_preview_key(self):
        return has_valid_preview_key()

    @cached_property
    def team_permissions_enabled(self):
        return frappe.db.get_single_value("Insights Settings", "enable_permissions")

    @cached_property
    def user_roles(self):
        return frappe.get_roles(self.user)

    def get_permission_query_conditions(self, doctype: str) -> str:
        if doctype not in PERMISSION_DOCTYPES:
            return ""

        if self.is_admin or self.has_preview_key:
            return ""

        if doctype == "Insights Team":
            # membership is the whole grant here, so a user with no teams sees
            # no team — the same answer `has_doc_permission` gives below
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

        # the preview browser reads a dashboard the way any viewer does, under a
        # key this site minted moments ago and holds only while the shot is taken
        if ptype == "read" and self.has_preview_key:
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

    def _build_audience_query(self, doctype, ptype):
        """Returns a query to get docs whose declared audience admits this user.

        The visibility ladder is one grant source beside owner, DocShare and
        the workbook/dashboard links. It is view-only: no rung ever grants
        write or share, and no rung consults the `Insights User` role.
        """
        if ptype != "read" or doctype not in VISIBILITY_LADDER_DOCTYPES:
            return None

        Content = frappe.qb.DocType(doctype)

        if self.user == "Guest":
            # the ladder is strict, so a guest only ever reaches the top rung
            return frappe.qb.from_(Content).select(Content.name).where(Content.visibility == "Public")

        query = frappe.qb.from_(Content).select(Content.name)
        admits_user = Content.visibility.isin(OPEN_AUDIENCES)

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
            admits_user = admits_user | (
                (Content.visibility == "Specific Roles") & NamedRoles.name.isnotnull()
            )

        return query.where(admits_user)

    def _with_audience_grant(self, query, Content, doctype, ptype, granted):
        """Adds the visibility ladder to a doctype's grant sources"""
        audience = self._build_audience_query(doctype, ptype)
        if audience is None:
            return query.where(granted)

        return (
            query.left_join(audience)
            .on(Content.name == audience.name)
            .where(granted | audience.name.isnotnull())
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
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
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

        return self._with_audience_grant(query, Dashboard, "Insights Dashboard v3", ptype, granted)

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
                & ((DocShare.user == self.user) | (DocShare.everyone == 1))
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
            # a chart on a dashboard inherits the dashboard's audience,
            # downward only — see _build_dashboard_permission_query
            | LinkedWithAllowedDashboards.name.isnotnull()
            | AllowedCharts.name.isnotnull()
        )

        return self._with_audience_grant(query, Chart, "Insights Chart v3", ptype, granted)

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
        """Returns the resources of this doctype that this user's teams hold.

        A team grant is a team's to give, so it reaches the members of the
        granting team and nobody else. No teams therefore names nothing here,
        whether the user belongs to no team or team permissions are off.
        """
        Resource = frappe.qb.DocType("Insights Resource Permission")
        query = frappe.qb.from_(Resource).select(Resource.resource_name.as_("name"))

        if not self.user_teams:
            # `IN ()` is not valid SQL, so the empty set is spelled out
            return query.where(Resource.name.isnull())

        return query.where(
            (Resource.resource_type == doctype)
            & (Resource.resource_name.isnotnull())
            & (Resource.parent.isin(self.user_teams))
        )


def has_doc_permission(doc, ptype, user):
    return InsightsPermissions(user).has_doc_permission(doc, ptype)


def get_permission_query_conditions(user, doctype):
    return InsightsPermissions(user).get_permission_query_conditions(doctype)


def check_app_permission():
    """The authoring gate: may this person enter the builder?

    It answers for the app, not for a document, and it is never consulted for
    viewing. A dashboard's audience is the visibility ladder's business, and the
    reading surfaces mount for people who hold no Insights role at all. Editing
    is both questions at once — write rights on the document AND a seat — and
    `can_edit` in `api/viewer.py` is the one place that conjunction is made.
    """
    if frappe.session.user == "Administrator":
        return True

    roles = frappe.get_roles()
    if any(role in ["Insights User", "Insights Admin"] for role in roles):
        return True

    return False
