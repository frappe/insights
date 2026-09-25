# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Who may read or change Insights content, and through which grant.

Frappe calls this module in two places. `get_permission_query_conditions`
filters the documents a list shows. `has_doc_permission` answers for one
document. Both go through `InsightsPermissions`, so the two always agree.

A user's access is the union of the grants below, per doctype and per action.

    Source                         Applies to                          Actions
    Admin (`is_admin`)             every permissioned doctype          all
    Ownership                      workbook, source, table             all
    DocShare                       workbook - and dashboard, chart,    per share flags,
                                   named and read only                 read on a member
    Container inheritance          workbook -> items, folders and      follows container
                                   alerts, chart -> query
    Dashboard link                 dashboard -> chart                  read only
    Team resource grant            source, table - and dashboard,      all, but read
                                   chart (legacy)                      only on a
                                                                       dashboard or
                                                                       chart
    Team membership                team                                all
    Visibility                     dashboard, chart                    read only
    Preview key                    the previewed dashboard, its        read only
                                   charts, their queries
    Role (`check_app_permission`)  the Builder, not documents          -

The table is complete. A grant not in it does not exist. Add a row here before
adding a join for a new grant. Nothing reads the old `is_public` column except
the patch that moved it to `visibility`.

Details the table leaves out:

- On a chart or dashboard, a DocShare counts only when it names a user. An
  org-wide share is ignored there, because the `Everyone` level already allows
  every signed-in user. A workbook has no visibility, so its org-wide share
  counts for signed-in users. A guest holds no share of either kind.
- `has_doc_permission` is asked for read, share or write. Any other ptype is
  checked as write. Share on a workbook member is also checked as write: a user
  who may edit a workbook may share what is in it. The list query checks read
  only.
- A document that is not saved yet has no grant to look up, so it is allowed.
  The exception is a new workbook member: its workbook decides. For an alert,
  that is its query's workbook.
- Ownership grants data sources and tables only in `has_doc_permission`. The
  list query has no owner condition for them, so teams alone decide which ones
  a list shows. Owning a workbook member grants nothing, so a user removed from
  a workbook loses access to what they made in it.
"""

from functools import cached_property

import frappe
import frappe.share
from pypika.terms import LiteralValue

from insights.insights.doctype.insights_team.insights_team import (
    get_teams,
    is_admin,
)
from insights.preview_key import is_being_previewed

PERMISSION_DOCTYPES = [
    "Insights Data Source v3",
    "Insights Table v3",
    "Insights Team",
    "Insights Workbook",
    "Insights Query v3",
    "Insights Chart v3",
    "Insights Dashboard v3",
    "Insights Alert",
    "Insights Folder",
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

# Documents that belong to a workbook. Only the workbook grants write on them.
# An alert belongs to its query's workbook.
WORKBOOK_MEMBERS = [
    "Insights Query v3",
    "Insights Chart v3",
    "Insights Dashboard v3",
    "Insights Alert",
    "Insights Folder",
]

VISIBILITY_DOCTYPES = [
    "Insights Chart v3",
    "Insights Dashboard v3",
]

# Visibility levels, narrowest first. They match the options of the
# `visibility` field, and `test_visibility` checks that they do.
PRIVATE = "Private"
ROLES = "Roles"
EVERYONE = "Everyone"
PUBLIC = "Public"
VISIBILITY_LEVELS = [PRIVATE, ROLES, EVERYONE, PUBLIC]

# `Everyone` and wider. These allow a signed-in user who holds no other grant.
OPEN_LEVELS = VISIBILITY_LEVELS[VISIBILITY_LEVELS.index(EVERYONE) :]


def visibility_level(visibility: str | None) -> int:
    """The index of `visibility` in `VISIBILITY_LEVELS`.

    An unknown value allows nobody, so it counts as `Private`.
    """
    return VISIBILITY_LEVELS.index(visibility) if visibility in VISIBILITY_LEVELS else 0


def reach(doc) -> tuple[int, frozenset[str]]:
    """The level of `doc`'s visibility, and the roles it names at `Roles`.

    `Roles` with no role allows nobody, so it counts as `Private`. So does a
    missing document, such as one being created.
    """
    level = visibility_level(doc.visibility) if doc else 0
    if VISIBILITY_LEVELS[level] != ROLES:
        return level, frozenset()

    roles = frozenset(row.role for row in doc.get("visible_to_roles") or [])
    return (level, roles) if roles else (0, frozenset())


def reaches_anybody(doc) -> bool:
    """Whether `doc`'s visibility allows anyone.

    Every level above `Private` allows a group of users, not users named one by
    one as a share does.
    """
    return reach(doc)[0] > 0


def widens(before, doc) -> bool:
    """Whether `doc`'s visibility allows someone that `before`'s did not.

    Levels are ordered from `Private` to `Public`. When both are at `Roles`, it
    widens if `doc` names a role `before` did not. Roles are compared by name,
    not by who holds them now, so the answer does not change with role holders.
    """
    was_level, was_roles = reach(before)
    level, roles = reach(doc)
    if level == was_level == VISIBILITY_LEVELS.index(ROLES):
        return not roles <= was_roles
    return level > was_level


# Roles that the `Roles` level may not name. `All` is every signed-in user and
# `Guest` is every visitor. The `Everyone` and `Public` levels already cover
# them, with their own checks. Administrator is not an audience.
# `insights.api.user.get_roles` lists the other roles.
UNNAMEABLE_ROLES = ("All", "Guest", "Administrator")


def get_insights_users():
    """Everyone who may use Insights: an enabled holder of an Insights role.

    One definition serves both sides of sharing - the picker lists this set and
    `validate_shareable_users` accepts it - so a name the picker lists is never
    refused when the share is saved. Administrator is left out: it is nobody to
    browse for, though it can still own a workbook and be granted access to one.
    """
    from frappe.utils.user import get_users_with_role

    users = set()
    for role in INSIGHTS_ROLES:
        users.update(get_users_with_role(role))
    return users


def workbook_of(member) -> str | None:
    """The workbook a member belongs to. An alert belongs to its query's."""
    if member.doctype == "Insights Alert":
        return member.query and frappe.db.get_value("Insights Query v3", member.query, "workbook")
    return member.get("workbook")


def is_member_share(share) -> bool:
    """Whether a DocShare has the only shape allowed on a workbook member: read
    on a dashboard or chart, for a named user.

    Only the workbook grants write and share on a member. A query is read
    through its workbook or through a chart on it. A folder or an alert is read
    through its workbook only. The `Everyone` level replaces an org-wide share.
    """
    return (
        share.share_doctype in VISIBILITY_DOCTYPES
        and bool(share.user)
        and not share.everyone
        and not (share.write or share.share or share.submit)
    )


def validate_member_share(share, method=None):
    """Refuse a DocShare on a workbook member unless `is_member_share` allows it.

    `frappe.has_permission` checks shares after the controller refuses. So any
    other shape grants access the workbook does not. The check runs on the
    DocShare itself, because `frappe.share`, the desk Share sidebar and a plain
    insert all save one.
    """
    if share.share_doctype not in WORKBOOK_MEMBERS or is_member_share(share):
        return

    member = frappe.get_doc(share.share_doctype, share.share_name)
    workbook = workbook_of(member)
    frappe.throw(
        frappe._(
            "{0} is shared through its workbook {1}. Share the workbook, or name a person to read a dashboard or chart."
        ).format(
            frappe._(share.share_doctype),
            frappe.bold(frappe.db.get_value("Insights Workbook", workbook, "title") or workbook),
        ),
        frappe.ValidationError,
    )


def refuse_member_row_alone(row, method=None):
    """Refuse a child row of a workbook member that is saved on its own.

    `frappe.client.save` and `/api/resource` can save a child row directly.
    They check only write on the parent, so the member's checks on its rows are
    skipped: which charts a dashboard shows, which roles a level names, the
    standard guard. The member's own save does not run its rows' hooks, so a
    row whose hook runs was saved on its own.

    frappe resolves `parenttype` ignoring case and trailing spaces, but stores
    the string as sent. So check the resolved doctype name.
    """
    if not row.get("parenttype"):
        return

    parent_doctype = frappe.get_meta(row.parenttype).name
    if parent_doctype not in WORKBOOK_MEMBERS:
        return

    frappe.throw(
        frappe._("A {0} row is changed by saving its {1}, not on its own.").format(
            frappe._(row.doctype), frappe._(parent_doctype)
        ),
        frappe.ValidationError,
    )


def validate_shareable_users(emails):
    """Refuse to share content with anyone who is not an Insights user.

    A DocShare gives a named user the sharer's own access, and it extends down:
    a share on a dashboard reaches every chart on it and every query behind
    them. `can_read_rows` also counts it as the reader's own grant, which gives
    them the rows and the file download. So the app decides who may be named,
    not the user picker.

    The picker cannot always list the user. A user who may not look up others
    can still type an address, and it must name a real Insights user.
    """
    if not emails:
        return

    # Administrator owns the workbooks an import creates, so it stays on their
    # share list when one of them is shared again
    shareable = get_insights_users() | {"Administrator"}
    unknown = sorted(set(emails) - shareable)
    if unknown:
        frappe.throw(
            frappe._("Cannot share with {0} - they are not an Insights user").format(", ".join(unknown)),
            title=frappe._("Not an Insights user"),
        )


class InsightsPermissions:
    def __init__(self, user=None, ignore_visibility=False):
        self.user = user or frappe.session.user
        # A visibility level, and a dashboard's grant on its charts, let a
        # reader see a chart but not its rows. `can_read_rows` sets this to
        # leave both grants out.
        self.ignore_visibility = ignore_visibility
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

        # A preview render arrives as Guest with a key made for one dashboard.
        # The key is its only grant, and it covers only the documents the
        # rendered image shows. The check is here, not on one endpoint, because
        # the render calls the same endpoints as every other reader.
        if ptype == "read" and is_being_previewed(doc.doctype, doc.name):
            return True

        # Read whether the row exists, and who owns it, from the database and
        # never from `doc`. A whitelisted method can run on a document built
        # from the request body, as frappe's `/api/v2/method/run_doc_method`
        # does. There `owner` and `__islocal` are ordinary keys, and trusting
        # either gives the caller every chart on the site.
        #
        # `create` is the one check about a row that does not exist yet. The
        # unique name column protects it: an insert onto a taken name fails
        # whatever this returns. A copy restored from a file keeps the names in
        # the file, and those rows still exist.
        creating = ptype == "create" and doc.is_new()
        stored_owner = (
            frappe.db.get_value(doc.doctype, doc.name, "owner") if doc.name and not creating else None
        )
        is_new = creating or stored_owner is None
        if is_new and doc.doctype in ["Insights Data Source v3", "Insights Table v3"]:
            # let further permission checks handle it
            return True

        if doc.doctype == "Insights Team":
            return doc.name in self.user_teams

        is_owner = stored_owner == self.user
        access_type = "write" if ptype not in ["read", "share"] else ptype
        if doc.doctype in WORKBOOK_MEMBERS and access_type == "share":
            access_type = "write"

        # a new member is checked against the workbook it names, like a saved one
        workbook = is_new and doc.doctype in WORKBOOK_MEMBERS and workbook_of(doc)
        if workbook:
            docs = self._build_permission_query("Insights Workbook", access_type)
            return (
                docs.where(frappe.qb.DocType("Insights Workbook").name == workbook).limit(1).run(pluck="name")
            )

        # owning a workbook member grants nothing; its workbook decides
        if is_new or (is_owner and doc.doctype not in WORKBOOK_MEMBERS):
            return True

        docs = self._build_permission_query(doc.doctype, access_type)
        return docs.where(frappe.qb.DocType(doc.doctype).name == doc.name).limit(1).run(pluck="name")

    def get_granted(self, doctype, ptype="read") -> list[str]:
        """Names the user can access through a grant.

        The admin bypass is skipped, so an admin's list shows what was granted
        to them, not every document on the site.
        """
        return self._build_permission_query(doctype, ptype).run(pluck=True)

    def _build_permission_query(self, doctype, ptype):
        """Returns a query to get docs with `ptype`  permission"""
        if doctype in ("Insights Folder", "Insights Alert") or (
            ptype == "write" and doctype in WORKBOOK_MEMBERS
        ):
            return self._build_workbook_member_query(doctype, ptype)

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
        return query

    def _build_workbook_member_query(self, doctype, ptype):
        """Members of `doctype` whose workbook grants `ptype`.

        This is the only source of write on a member, and of any access to a
        folder or an alert. Neither is shown to readers or shared, so a reader
        of a chart cannot read an alert on its query. Owning a member, a share
        on it or a team grant on it gives read only. So a user removed from a
        workbook cannot edit what they made in it.
        """
        Member = frappe.qb.DocType(doctype)
        workbooks = self._build_workbook_permission_query(ptype)
        if doctype != "Insights Alert":
            return frappe.qb.from_(Member).select(Member.name).where(Member.workbook.isin(workbooks))

        Query = frappe.qb.DocType("Insights Query v3")
        return (
            frappe.qb.from_(Member)
            .join(Query)
            .on(Member.query == Query.name)
            .select(Member.name)
            .where(Query.workbook.isin(workbooks))
        )

    def _build_visibility_query(self, doctype, ptype):
        """Documents whose visibility allows this user.

        Visibility grants read only, never write or share. No level checks the
        `Insights User` role. Under `ignore_visibility` it allows nobody.
        """
        if ptype != "read" or doctype not in VISIBILITY_DOCTYPES or self.ignore_visibility:
            return None

        Content = frappe.qb.DocType(doctype)

        if self.user == "Guest":
            # a guest holds no role, so only `Public` allows them
            return frappe.qb.from_(Content).select(Content.name).where(Content.visibility == PUBLIC)

        query = frappe.qb.from_(Content).select(Content.name)
        allows_user = Content.visibility.isin(OPEN_LEVELS)

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
            named = (Content.visibility == ROLES) & NamedRoles.name.isnotnull()
            allows_user = allows_user | named

        return query.where(allows_user)

    def _with_visibility_grant(self, query, Content, doctype, ptype, granted):
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
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import desk_readable_tables

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

        # On a site DB source, desk read on a doctype lets the user read its
        # table, as a team grant does. `apply_user_permissions` filters rows by
        # the same rule. It grants read only: desk read does not allow changing
        # the Insights Table document.
        DataSource = frappe.qb.DocType("Insights Data Source v3")
        desk_tables = desk_readable_tables(self.user) if ptype == "read" else set()
        TablesDeskReads = (
            frappe.qb.from_(Table)
            .select(Table.name.as_("name"))
            .inner_join(DataSource)
            .on(Table.data_source == DataSource.name)
            .where(
                (DataSource.is_site_db == 1)
                & (Table.table.isin(list(desk_tables)) if desk_tables else LiteralValue("1 = 0"))
            )
        )

        return (
            frappe.qb.from_(Table)
            .select(Table.name)
            .left_join(AllowedTables)
            .on(Table.name == AllowedTables.name)
            .left_join(TablesOfAllowedSources)
            .on(Table.name == TablesOfAllowedSources.name)
            .left_join(TablesDeskReads)
            .on(Table.name == TablesDeskReads.name)
            .where(
                AllowedTables.name.isnotnull()
                | TablesOfAllowedSources.name.isnotnull()
                | TablesDeskReads.name.isnotnull()
            )
        )

    def _build_docshare_query(self, doctype, ptype, org_wide=False):
        """Documents of `doctype` that a DocShare grants `ptype` on.

        A share names a user, and an org-wide share means every signed-in user.
        So no share applies to a guest, as in Frappe's own `get_shared`. The
        `Public` level is a guest's only grant.
        """
        DocShare = frappe.qb.DocType("DocShare")

        if self.user == "Guest":
            names_the_user = LiteralValue("1 = 0")
        else:
            names_the_user = DocShare.user == self.user
            if org_wide:
                names_the_user = names_the_user | (DocShare.everyone == 1)

        return (
            frappe.qb.from_(DocShare)
            .select(DocShare.share_name)
            .where((DocShare.share_doctype == doctype) & (DocShare[ptype] == 1) & names_the_user)
        )

    def _build_workbook_permission_query(self, ptype):
        Workbook = frappe.qb.DocType("Insights Workbook")

        OwnedWorkbooks = frappe.qb.from_(Workbook).select(Workbook.name).where(Workbook.owner == self.user)

        SharedWorkbooks = self._build_docshare_query("Insights Workbook", ptype, org_wide=True)

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
        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .left_join(AllowedWorkbooks)
            .on(Dashboard.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        SharedDashboards = self._build_docshare_query("Insights Dashboard v3", ptype)

        query = (
            frappe.qb.from_(Dashboard)
            .select(Dashboard.name)
            .left_join(SharedDashboards)
            .on(Dashboard.name == SharedDashboards.share_name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Dashboard.name == LinkedWithAllowedWorkbooks.name)
        )
        granted = SharedDashboards.share_name.isnotnull() | LinkedWithAllowedWorkbooks.name.isnotnull()

        # a team grant on a dashboard gives read only
        if ptype == "read":
            AllowedDashboards = self._build_resource_query("Insights Dashboard v3")
            query = query.left_join(AllowedDashboards).on(Dashboard.name == AllowedDashboards.name)
            granted = granted | AllowedDashboards.name.isnotnull()

        return self._with_visibility_grant(query, Dashboard, "Insights Dashboard v3", ptype, granted)

    def _build_chart_permission_query(self, ptype):
        Chart = frappe.qb.DocType("Insights Chart v3")
        DashboardChart = frappe.qb.DocType("Insights Dashboard Chart v3")

        SharedCharts = self._build_docshare_query("Insights Chart v3", ptype)

        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(AllowedWorkbooks)
            .on(Chart.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        query = (
            frappe.qb.from_(Chart)
            .select(Chart.name)
            .left_join(SharedCharts)
            .on(Chart.name == SharedCharts.share_name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Chart.name == LinkedWithAllowedWorkbooks.name)
        )
        granted = SharedCharts.share_name.isnotnull() | LinkedWithAllowedWorkbooks.name.isnotnull()

        # a team grant on a chart gives read only
        if ptype == "read":
            AllowedCharts = self._build_resource_query("Insights Chart v3")
            query = query.left_join(AllowedCharts).on(Chart.name == AllowedCharts.name)
            granted = granted | AllowedCharts.name.isnotnull()

        # A dashboard gives its readers read on every chart on it, as a
        # visibility level does. Never write, delete or share: otherwise anyone
        # who may save a dashboard could act on a chart through it. It gives no
        # read on the queries behind the chart; `_named_grants` leaves it out.
        if ptype == "read" and not self.ignore_visibility:
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
            query = query.left_join(LinkedWithAllowedDashboards).on(
                Chart.name == LinkedWithAllowedDashboards.name
            )
            granted = granted | LinkedWithAllowedDashboards.name.isnotnull()

        return self._with_visibility_grant(query, Chart, "Insights Chart v3", ptype, granted)

    def _build_query_permission_query(self, ptype):
        Query = frappe.qb.DocType("Insights Query v3")

        AllowedWorkbooks = self._build_workbook_permission_query(ptype)

        LinkedWithAllowedWorkbooks = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(AllowedWorkbooks)
            .on(Query.workbook == AllowedWorkbooks.name)
            .where(AllowedWorkbooks.name.isnotnull())
        )

        query = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(LinkedWithAllowedWorkbooks)
            .on(Query.name == LinkedWithAllowedWorkbooks.name)
        )

        granted = LinkedWithAllowedWorkbooks.name.isnotnull()

        if ptype != "read":
            return query.where(granted)

        # A chart's grant gives read on the queries its pipeline reads in its
        # own workbook. It never gives write or delete; those belong to the
        # workbook. It does not apply to a reader allowed in only by a visibility
        # level or a dashboard: they may see the chart, not its pipeline.
        Chart = frappe.qb.DocType("Insights Chart v3")
        AllowedCharts = self._named_grants._build_chart_permission_query("read").select(
            Chart.query, Chart.workbook
        )

        LinkedWithAllowedCharts = (
            frappe.qb.from_(Query)
            .select(Query.name)
            .left_join(AllowedCharts)
            .on((Query.name == AllowedCharts.query) & (Query.workbook == AllowedCharts.workbook))
            .where(AllowedCharts.name.isnotnull())
        )

        query = query.left_join(LinkedWithAllowedCharts).on(Query.name == LinkedWithAllowedCharts.name)
        granted = granted | LinkedWithAllowedCharts.name.isnotnull()

        # Also every query those queries read from, at any depth.
        # `_queries_sourced_under_allowed_charts` explains why only the first
        # hop is a join.
        sourced = self._queries_sourced_under_allowed_charts
        if sourced:
            granted = granted | Query.name.isin(sorted(sourced))

        return query.where(granted)

    @cached_property
    def _named_grants(self):
        """This user's permissions without the grants that only show a chart:
        visibility levels, and a dashboard's grant on its charts."""
        return self if self.ignore_visibility else InsightsPermissions(self.user, ignore_visibility=True)

    @cached_property
    def _queries_sourced_under_allowed_charts(self):
        """Every query read, at any depth, by the queries of charts this user may read.

        A chart's grant extends to the query behind it, because the card shows
        what that query returned. It must reach as deep as the engine reads.
        `IbisQueryBuilder.check_query_reference` trusts a saved reference, so
        the card's number is already computed through every query below it. A
        grant that stopped at `Chart.query` refused the list of values for a
        column of that chart. It stays in the chart's own workbook, as the
        first hop does.

        Read each query's own `operations`, not the edge table. A background
        job rebuilds that table after the save commits, so a grant read from it
        refuses the author a dashboard they just saved.

        Only the hops past the first are found here. The first hop stays a
        join, because computing the chart grant for every query in the graph is
        what makes a walk expensive. The walk starts from queries that another
        query reads from, since only those can be more than one hop away. A
        site with no layered queries pays one indexed scan and no join.
        """
        from insights.insights.query_utils import referenced_queries

        sources = {}
        for row in frappe.get_all(
            "Insights Query v3",
            filters={"operations": ("like", "%query_name%")},
            fields=["name", "operations"],
        ):
            referenced = referenced_queries(row.operations)
            if referenced:
                sources[row.name] = referenced

        reachable = set()
        if sources:
            names = set(sources) | {ref for refs in sources.values() for ref in refs}
            workbooks = dict(
                frappe.get_all(
                    "Insights Query v3",
                    filters={"name": ("in", sorted(names))},
                    fields=["name", "workbook"],
                    as_list=True,
                )
            )

            Chart = frappe.qb.DocType("Insights Chart v3")
            read_by_a_chart = (
                frappe.qb.from_(Chart)
                .select(Chart.query, Chart.workbook)
                .where(
                    Chart.query.isin(sorted(sources))
                    & Chart.name.isin(self._named_grants._build_chart_permission_query("read"))
                )
                .run()
            )
            for query, workbook in read_by_a_chart:
                if workbooks.get(query) != workbook:
                    continue
                frontier = {ref for ref in sources[query] if workbooks.get(ref) == workbook}
                while frontier:
                    reachable |= frontier
                    frontier = {
                        ref
                        for name in frontier
                        for ref in sources.get(name, ())
                        if workbooks.get(ref) == workbook
                    } - reachable

        return reachable

    def _build_resource_query(self, doctype):
        """Grants on `doctype` that the user holds through a team.

        A team is the only thing that holds a grant, so a user in no team must
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

    An unattended execution has no caller, so it is checked against the user it
    runs as (`get_permission_user`).

    It asks `may_read`, not `frappe.has_permission`. A reader allowed on a
    dashboard by its visibility may hold no Insights role. Frappe's role check
    would refuse them a query that the chart they are reading grants them.
    """
    if not can_read_referenced_query(query_name):
        frappe.throw(
            frappe._("You do not have access to a query this one references"),
            frappe.PermissionError,
        )


def can_read_referenced_query(query_name) -> bool:
    """`check_referenced_query_access` as a boolean, for a caller with a fallback.

    A dashboard filter tries several links and uses the first readable one.
    Throwing on the first unreadable link would refuse the filter for the rest.
    """
    from insights.permission_user import get_permission_user
    from insights.resolver import may_read

    # a name with no row resolves to nothing. The build says "not found" instead.
    if not frappe.db.exists("Insights Query v3", query_name):
        return True

    return bool(may_read(frappe.get_doc("Insights Query v3", query_name), get_permission_user()))


def can_read_chart(chart_name) -> bool:
    """Whether the caller may read a chart, checked like a referenced query.

    Whoever may read a chart may read every query its stored pipeline reads. So
    an endpoint limited to that pipeline (`chart_reads`) checks the chart, not
    the query. A reader allowed only by a visibility level has no grant on the
    query, but may still see what the chart shows from it.
    """
    from insights.permission_user import get_permission_user
    from insights.resolver import may_read

    return bool(may_read(frappe.get_doc("Insights Chart v3", chart_name), get_permission_user()))


def check_chart_query_access(chart):
    """A chart may only point at a query its writer can read.

    The link is a grant, not a reference: `_build_query_permission_query` gives
    read on every query linked from a chart the caller can read. So the link has
    to be checked where it is written, or it widens the writer's own access.

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
    """Widening a document's visibility needs share permission, not write.

    `visibility` and `visible_to_roles` are ordinary fields, so any write can
    change them. Widening them gives the owner's read access to users who have
    none of their own, and at `Public` to a guest on the open internet. That is
    what share means. So it is checked on save, like a chart's query link.

    Only widening is checked. Narrowing takes nothing from anyone. A new
    document allows nobody before its first save, so any level it has is a
    widening. A copy is reset instead of allowed; see
    `InsightsChartv3.duplicate`.
    """
    before = doc.get_doc_before_save()
    was_roles = {row.role for row in (before.get("visible_to_roles") or [])} if before else set()
    refuse_unnameable_roles({row.role for row in (doc.get("visible_to_roles") or [])} - was_roles)

    if not widens(before, doc):
        return

    if not frappe.has_permission(doc.doctype, ptype="share", doc=doc if doc.is_new() else doc.name):
        frappe.throw(
            frappe._("You do not have permission to change who can see this"),
            frappe.PermissionError,
        )


def capture_visibility_widened(doc):
    """Send `share_granted` for a save that moved `doc` up to an open level.

    Called from `on_update`, so a save that a later validator refuses sends nothing.
    """
    if (
        doc.visibility in OPEN_LEVELS
        and visibility_level(doc.visibility) > reach(doc.get_doc_before_save())[0]
    ):
        from insights.telemetry import capture_share_granted

        shared = "chart" if doc.doctype == "Insights Chart v3" else "dashboard"
        capture_share_granted(shared, "public" if doc.visibility == PUBLIC else "org", 1)


def refuse_unnameable_roles(added: set[str]) -> None:
    refused = sorted(added & set(UNNAMEABLE_ROLES))
    if not refused:
        return

    frappe.throw(
        frappe._("{0} cannot be named here. Use the Everyone or Public level instead.").format(
            ", ".join(frappe.bold(role) for role in refused)
        ),
        frappe.ValidationError,
    )


def validate_run_as_owner(chart):
    """Check who may change `run_as_owner`, what Public requires, and that a standard chart never sets it.

    Only the owner or an admin may set it. When it is set, every read of the
    chart filters by another user's permissions, and neither share nor write on
    a chart grants that. Any writer may clear it, because clearing it exposes
    nobody's rows.

    A guest has no permissions of their own. So a chart that moves to Public
    sets it, and clearing it is refused while the chart is Public or on a
    Public dashboard. Otherwise a guest would see an empty page there. Each
    rule checks a change, never a saved value: `run_public_charts_as_owner`
    leaves it off where it cannot know whose rows to show.

    A standard chart's owner is Administrator on every site. If it were set,
    every reader would see every row of a chart the site did not write. A site
    that wants to show a number more widely sets it on a copy.
    """
    # checked before the Public rule below sets it, because that change is not the caller's
    if chart.has_value_changed("run_as_owner") and not may_move_run_as_owner(chart):
        frappe.throw(
            frappe._("Only the owner of a chart can change whose permissions it runs with."),
            frappe.PermissionError,
        )

    if chart.visibility == PUBLIC and chart.has_value_changed("visibility"):
        chart.run_as_owner = 1

    if chart.run_as_owner:
        if publishes(chart):
            check_owner_publishes(chart)
    elif chart.has_value_changed("run_as_owner"):
        if chart.visibility == PUBLIC:
            frappe.throw(
                frappe._("A public chart runs as its owner, so it cannot run as its reader."),
                frappe.ValidationError,
            )

        public_dashboard = public_dashboards_linking(chart)
        if public_dashboard:
            frappe.throw(
                frappe._(
                    "This chart is on the public dashboard {0}, so it runs as its owner and cannot run as its reader."
                ).format(public_dashboard),
                frappe.ValidationError,
            )

    if chart.is_standard and chart.run_as_owner:
        frappe.throw(
            frappe._("A standard chart runs as its reader, so it cannot run as its owner."),
            frappe.ValidationError,
        )


def publishes(doc) -> bool:
    """Whether this save widens `doc`'s visibility above `Private`.

    `Roles` counts as much as `Public`: the owner's rows go to everyone with the
    role, as they go to anyone with a link.
    """
    return reaches_anybody(doc) and widens(doc.get_doc_before_save(), doc)


def check_owner_publishes(chart, through=None):
    """Only the owner may publish a chart that runs as its owner.

    Such a chart shows every reader the owner's rows. Share cannot grant that:
    it gives out the sharer's own access, never another user's. Write on a
    chart is not ownership either, which is also why `validate_run_as_owner`
    leaves the setting to the owner.

    Two saves can widen a chart's reach: the chart's own save, and the save of
    a dashboard it is on, since `_build_chart_permission_query` gives the
    dashboard's readers read on its charts. `through` is that dashboard, so the
    message names the document the caller saved.

    The check reads the field, not whose rows the chart shows today. An owner
    who lost write on the chart shows nobody their rows now, but would again
    once they get write back.
    """
    if not chart.run_as_owner:
        return

    if may_send_owner_rows(chart):
        return

    if through:
        frappe.throw(
            frappe._(
                "{0} cannot be published: {1} on it runs with its owner's permissions, so only its owner can publish it."
            ).format(frappe.bold(through.title), frappe.bold(chart.title)),
            frappe.PermissionError,
        )

    frappe.throw(
        frappe._("{0} runs with its owner's permissions, so only its owner can publish it.").format(
            frappe.bold(chart.title)
        ),
        frappe.PermissionError,
    )


def may_move_run_as_owner(chart, user: str | None = None) -> bool:
    """Whether this user may change `chart`'s `run_as_owner` from its saved value.

    Setting it needs `may_send_owner_rows`. Clearing it needs write. The share
    dialog enables its toggle from this answer, so the client has no rule of
    its own for who is an admin.
    """
    user = user or frappe.session.user
    saved = chart.name and frappe.db.get_value(chart.doctype, chart.name, "run_as_owner")
    if saved:
        return bool(frappe.has_permission(chart.doctype, ptype="write", doc=chart.name, user=user))
    return may_send_owner_rows(chart, user)


def may_send_owner_rows(chart, user: str | None = None) -> bool:
    """Whether this user may show `chart`'s owner's rows to its readers: the owner or an admin."""
    user = user or frappe.session.user
    return user == chart.owner or is_admin(user)


def dashboard_linking_at(chart, levels: list[str], reader: str | None = None) -> str | None:
    """The title of a dashboard at one of `levels` that shows this chart.

    A dashboard's readers may read every chart on it, so a Private chart on a
    published dashboard is published. `validate_run_as_owner` uses this to ask
    whether a guest reads the chart, and `published_reach` to ask what the
    share dialog should warn about.

    With a `reader`, only dashboards they may read count, because the title is
    shown to them.
    """
    if chart.is_new():
        return None

    Dashboard = frappe.qb.DocType("Insights Dashboard v3")
    DashboardChart = frappe.qb.DocType("Insights Dashboard Chart v3")

    HasRole = frappe.qb.DocType("Has Role")
    naming_a_role = (
        frappe.qb.from_(HasRole)
        .select(HasRole.parent)
        .where((HasRole.parenttype == "Insights Dashboard v3") & (HasRole.parentfield == "visible_to_roles"))
    )

    dashboards = (
        frappe.qb.from_(DashboardChart)
        .join(Dashboard)
        .on(Dashboard.name == DashboardChart.parent)
        .select(Dashboard.title)
        .where(
            (DashboardChart.parenttype == "Insights Dashboard v3")
            & (DashboardChart.chart == chart.name)
            & (Dashboard.visibility.isin(levels))
            # `Roles` naming no role allows nobody (`reach`)
            & ((Dashboard.visibility != ROLES) | Dashboard.name.isin(naming_a_role))
        )
        .limit(1)
    )
    if reader and not is_admin(reader):
        readable = InsightsPermissions(reader)._build_dashboard_permission_query("read")
        dashboards = dashboards.where(Dashboard.name.isin(readable))

    dashboards = dashboards.run(pluck=True)

    return dashboards[0] if dashboards else None


def public_dashboards_linking(chart) -> str | None:
    """The title of a Public dashboard this chart is linked to, if there is one."""
    return dashboard_linking_at(chart, [PUBLIC])


def published_reach(chart) -> dict:
    """How far this chart reaches in practice, for the share dialog's `run_as_owner` toggle.

    Its own level is half the answer. The other half is the dashboards it is
    on: the widest one publishes it whatever the chart's own level. A `Private`
    chart on a Public dashboard is what `run_public_charts_as_owner` leaves
    behind. The share dialog shows its red confirmation from this. Without it,
    turning the setting on would send the owner's rows to everyone on that
    dashboard with no warning.
    """
    return {
        "published": reaches_anybody(chart),
        "published_by_dashboard": dashboard_linking_at(
            chart, VISIBILITY_LEVELS[VISIBILITY_LEVELS.index(ROLES) :], reader=frappe.session.user
        ),
        # `validate_run_as_owner` refuses clearing it here, so the toggle does
        # not allow it
        "on_public_dashboard": bool(public_dashboards_linking(chart)),
    }


def check_dashboard_publishes(dashboard):
    """Apply the owner rules to the charts on a published dashboard.

    `_build_chart_permission_query` gives the dashboard's readers read on every
    chart on it, whatever the chart's own level. So a dashboard above `Private`
    publishes its charts, `Roles` included, and the dashboard's save checks
    them.

    A guest has no permissions of their own, so a Public dashboard may show
    only charts that run as their owner. Only a chart's owner may set that, so
    the save is refused with the charts named, and no chart is changed. A chart
    that runs as its owner shows the owner's rows to the dashboard's readers,
    so `check_owner_publishes` checks the user who saves.
    """
    if not reaches_anybody(dashboard):
        return

    runs_as_reader = []
    for name in charts_newly_published(dashboard):
        chart = frappe.get_doc("Insights Chart v3", name)

        # a standard chart never runs as its owner (`validate_run_as_owner`),
        # so publishing it exposes nobody's rows
        if chart.is_standard:
            continue

        if not chart.run_as_owner:
            if dashboard.visibility == PUBLIC:
                runs_as_reader.append(chart.title or chart.name)
            continue

        check_owner_publishes(chart, through=dashboard)

    if runs_as_reader:
        frappe.throw(
            frappe._(
                "{0} cannot be public until every chart on it runs as its owner. A guest has no permissions of their own, so these charts would show them nothing: {1}"
            ).format(
                frappe.bold(dashboard.title),
                ", ".join(frappe.bold(title) for title in runs_as_reader),
            ),
            frappe.ValidationError,
        )


def charts_newly_published(dashboard) -> list[str]:
    """The charts this save shows to readers who could not read them before.

    If the visibility widens, that is every chart on the dashboard. Otherwise
    it is only the charts the save adds. A new card on a published dashboard
    reaches the same readers, and the dashboard's save is the only save.

    Checking every chart on every save would refuse a layout edit on a
    dashboard that shows another user's chart. It would also undo what
    `run_public_charts_as_owner` leaves unchecked on purpose.
    """
    if widens(dashboard.get_doc_before_save(), dashboard):
        return [row.chart for row in dashboard.linked_charts]

    return charts_newly_linked(dashboard)


def charts_newly_linked(dashboard) -> list[str]:
    """The linked charts this save adds to the grid."""
    before = dashboard.get_doc_before_save()
    was_linked = {row.chart for row in before.linked_charts} if before else set()
    return [row.chart for row in dashboard.linked_charts if row.chart not in was_linked]


def check_dashboard_chart_access(dashboard):
    """A dashboard may show only charts of its own workbook that its writer can read.

    `_build_chart_permission_query` grants read on every chart on a dashboard
    the caller can read, so adding a chart here is a grant too. The dashboard's
    filters also narrow every chart on it. Only the chart's workbook may do
    that, not a user who only reads the chart.

    Only the charts this save adds are checked. Deleting a chart saves every
    dashboard that shows it, and the user deleting it need not read the rest
    of another user's dashboard.
    """
    charts = charts_newly_linked(dashboard)
    workbooks = dict(
        frappe.get_all(
            "Insights Chart v3",
            filters={"name": ("in", charts)},
            fields=["name", "workbook"],
            as_list=True,
        )
    )
    for chart in charts:
        if not frappe.has_permission("Insights Chart v3", ptype="read", doc=chart):
            frappe.throw(
                frappe._("You do not have access to one of the charts on this dashboard"),
                frappe.PermissionError,
            )
        if workbooks.get(chart) != dashboard.workbook:
            frappe.throw(
                frappe._("A dashboard can only show charts of its own workbook"),
                frappe.ValidationError,
            )


def has_doc_permission(doc, ptype, user):
    return InsightsPermissions(user).has_doc_permission(doc, ptype)


def get_permission_query_conditions(user, doctype):
    return InsightsPermissions(user).get_permission_query_conditions(doctype)


def can_read_rows(doc, user=None) -> bool:
    """Whether this caller may get more of `doc` than the chart as saved.

    More means a breakdown, the rows behind a segment, a file download, a card
    filter of their own, a page past the chart's `limit`, and the SQL and
    operations it ran. The chart as saved is the stored chart and its dashboard
    filters. Every endpoint that answers for a chart checks this:
    `insights.api.view`, `insights.api.authoring`, the chart's `fetch` and its
    drill.

    Visibility cannot grant this. It publishes the chart, and the rows behind
    it hold columns the card never shows.

    A guest gets the chart as saved only. A chart that runs as its reader shows
    anyone else only their own rows, so they may have more. A chart that runs
    as its owner (`declared_owner`) needs write: whoever may change what runs as
    the owner is trusted to act as them. Other documents need a grant that
    names this user: DocShare, workbook or team.

    Checked against the saved row, because a whitelisted method's `self` is
    built from the request body. A name with no row is the caller's own unsaved
    pipeline.
    """
    user = user or frappe.session.user

    if user == "Guest":
        return False

    if not doc.name or not frappe.db.exists(doc.doctype, doc.name):
        return True

    if doc.doctype == "Insights Chart v3":
        from insights.permission_user import declared_owner

        if not declared_owner(doc):
            return True
        return bool(frappe.has_permission(doc.doctype, ptype="write", doc=doc.name, user=user))

    stored = frappe.get_doc(doc.doctype, doc.name)
    return bool(InsightsPermissions(user, ignore_visibility=True).has_doc_permission(stored, "read"))


def can_download(user=None) -> bool:
    """Whether this user may download data as a file at all.

    It depends on the user, never on a document: the site's `allow_download`
    setting, which an Insights Admin ignores, and the role's `export`
    permission, because downloading data is a role's decision. `get_user_info`
    returns it so the client can show the control.

    The role is checked on `Insights Query v3` always, so the answer does not
    depend on which doctype the caller came through. It is checked only for a
    user with an Insights role. Every view endpoint is open to readers with no
    Insights role, allowed by name through a DocShare. A ptype on a doctype
    whose roles they lack says nothing about them. Reading it as a refusal
    would confuse "has no Insights role" with "has a role the site denied
    export".
    """
    user = user or frappe.session.user

    # a guest gets only the chart as saved (`can_read_rows`), so never a file
    if user == "Guest":
        return False

    if is_admin(user):
        return True

    if not frappe.db.get_single_value("Insights Settings", "allow_download"):
        return False

    if not any(role in INSIGHTS_ROLES for role in frappe.get_roles(user)):
        return True

    return bool(frappe.has_permission("Insights Query v3", ptype="export", user=user))


def can_export(doc, user=None) -> bool:
    """Whether this user may download *these* rows as a file.

    The document is required, so no caller checks only `can_download`. The
    document half is `can_read_rows`: visibility publishes the chart, not the
    rows behind it.
    """
    return can_download(user) and can_read_rows(doc, user or frappe.session.user)


def can_write(doc) -> bool:
    """Whether the caller may change `doc`. Every edit control checks this.

    The form's `read_only`, a view's `can_write` and the Builder's
    `authoring.is_writer` all read it. It needs write on the document, an
    Insights role, and a workbook the site may change. Standard content is
    read-only outside developer mode, even to its owner, and `can_copy` allows
    a copy instead.
    """
    from insights import standard

    workbook = doc.name if doc.doctype == "Insights Workbook" else workbook_of(doc)
    if standard.is_read_only(workbook):
        return False

    return bool(frappe.has_permission(doc.doctype, ptype="write", doc=doc)) and check_app_permission()


def can_copy(doc) -> bool:
    """Whether the caller may duplicate `doc`'s workbook instead of editing it.

    Standard content is read-only on a site, so a copy is the only way to
    change it. Changing it needs an Insights role.
    """
    from insights import standard

    workbook = doc.name if doc.doctype == "Insights Workbook" else workbook_of(doc)
    return (
        standard.is_read_only(workbook)
        and check_app_permission()
        and bool(frappe.has_permission("Insights Workbook", ptype="read", doc=workbook))
    )


def can_share(doc) -> bool:
    """Whether the caller may widen who reads `doc` or share it with a user.

    The Builder shows Share from this. On a workbook member, share is write on
    its workbook today, so this matches `can_write`. It stays separate so that
    a workbook permission to edit without sharing would change only this.
    """
    return can_write(doc) and bool(frappe.has_permission(doc.doctype, ptype="share", doc=doc))


def check_app_permission(user=None):
    """Whether this user may open the Builder.

    It is about the app, not a document, and a view never checks it.
    `visibility` decides who reads a dashboard, and a view renders for users
    with no Insights role. Editing needs both write on the document and a role;
    `can_write` is the one place that checks both.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return True

    return any(role in INSIGHTS_ROLES for role in frappe.get_roles(user))


def check_trusted_code_author(documents) -> None:
    """Only an Insights Admin adds or changes trusted code (`trusted_code_of`).

    `documents` holds `(title, content, stored content)` for each query, chart or
    alert being saved. Stored content is empty for a new one. Trusted code that
    is already stored keeps running and saving for any writer. Other trusted
    code is refused, and the message names every document that adds some.
    Checked on save, and before an import's or a copy's queries and charts are
    inserted, so one message names them all. Also checked on a run, such as a
    build or an alert's send, because a run uses unsaved content.
    """
    if is_admin(frappe.session.user):
        return

    titles = [
        title for title, content, stored in documents if trusted_code_of(content) - trusted_code_of(stored)
    ]
    if titles:
        frappe.throw(
            frappe._(
                "Only an Insights Admin can add or change a script, an expression that runs SQL or a stored procedure call: {0}"
            ).format(", ".join(frappe.bold(frappe.utils.escape_html(title)) for title in titles)),
            frappe.PermissionError,
        )


def trusted_code_of(content) -> set[str]:
    """Trusted code in a query's operations, a chart's config or an alert's
    condition: a script, an expression that runs SQL, and a SQL query that calls
    a stored procedure.

    `Table.sql` and a stored procedure read any table on the connection and
    ignore the reader's permissions. A script may do that; an expression or a
    SQL query may not.
    """
    from insights.insights.doctype.insights_data_source_v3.ibis.utils import runs_sql
    from insights.insights.query_utils import runs_stored_procedure

    found = set()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "code":
                found.add(node.get("code") or "")
            raw_sql = node.get("raw_sql")
            if node.get("type") == "sql" and isinstance(raw_sql, str) and runs_stored_procedure(raw_sql):
                found.add(raw_sql)
            expression = node.get("expression")
            if isinstance(expression, str) and runs_sql(expression):
                found.add(expression)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(frappe.parse_json(content) if isinstance(content, str) else content)
    return found
