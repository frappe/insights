# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Who may read or change Insights content, and on which grant.

Frappe asks this module two questions. `get_permission_query_conditions` names
the documents a list may show. `has_doc_permission` answers for one document.
Both run through `InsightsPermissions`, so a grant one seam honors the other
honors too.

One rule holds under all of it: a grant is the union of enumerable sources, per
doctype and per action.

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
  org-wide share is read - by a signed-in user. A guest holds no share of
  either kind, because both name people and a guest is nobody.

- Actions fold. `has_doc_permission` is asked for read, share or write, and
  anything that is neither read nor share is asked as write. Share on a
  workbook member is asked as write too: whoever may edit a workbook shares and
  publishes what is in it. The list seam asks for read and nothing else.
- A document that does not exist yet has nothing to enumerate, so the controller
  admits it. The one exception is a new workbook member, where its workbook's
  grant decides - an alert's is its query's.
- Ownership is a source for data sources and tables on the document seam only.
  The list seam builds no owner branch for them: teams alone say which of those
  a list may show. A workbook member's owner holds nothing by owning it, so a
  person removed from a workbook loses what they made there.
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

# content that lives in a workbook: write on it is the workbook's alone. An
# alert's workbook is its query's.
WORKBOOK_MEMBERS = [
    "Insights Query v3",
    "Insights Chart v3",
    "Insights Dashboard v3",
    "Insights Alert",
    "Insights Folder",
]

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

# `Everyone` and every level wider: they admit a signed-in reader who holds
# nothing of their own
OPEN_LEVELS = VISIBILITY_LEVELS[VISIBILITY_LEVELS.index(EVERYONE) :]


def visibility_level(visibility: str | None) -> int:
    """Where a declared visibility sits on `VISIBILITY_LEVELS`.

    A visibility the field does not name reaches nobody, because every level is
    matched by its exact name. So it sits at the bottom beside `Private`.
    """
    return VISIBILITY_LEVELS.index(visibility) if visibility in VISIBILITY_LEVELS else 0


def reach(doc) -> tuple[int, frozenset[str]]:
    """Who `doc`'s declared visibility admits: its level, and the roles `Roles` names.

    Roles are read at `Roles` only, the one level that reads them. `Roles`
    naming no role admits nobody, the same as `Private`. No document at all -
    one being created - admits nobody either.
    """
    level = visibility_level(doc.visibility) if doc else 0
    if VISIBILITY_LEVELS[level] != ROLES:
        return level, frozenset()

    roles = frozenset(row.role for row in doc.get("visible_to_roles") or [])
    return (level, roles) if roles else (0, frozenset())


def reaches_anybody(doc) -> bool:
    """Whether `doc`'s level admits a population: readers nobody named one at a time.

    That is every reach but nobody. A role names a group and not a person,
    and the open levels name nobody at all, so no one on them was named the way
    `share` names a person.
    """
    return reach(doc)[0] > 0


def widens(before, doc) -> bool:
    """Whether `doc`'s reach holds somebody `before`'s did not.

    Reaches nest: nobody, then `Roles` naming R, then `Roles` naming more than
    R, then `Everyone`, then `Public`. Two role sets compare by the roles and not
    by who holds them today, so the answer does not move when role holders do.
    """
    was_level, was_roles = reach(before)
    level, roles = reach(doc)
    if level == was_level == VISIBILITY_LEVELS.index(ROLES):
        return not roles <= was_roles
    return level > was_level


# Roles a document may not name at `Roles`. `All` is every signed-in user and
# `Guest` is every visitor, which the `Everyone` and `Public` levels already say
# and say under the guard that belongs to them; Administrator is nobody to
# publish to. The picker in `insights.api.user.get_roles` offers what is left.
UNNAMEABLE_ROLES = ("All", "Guest", "Administrator")


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


def workbook_of(member) -> str | None:
    """The workbook a member lives in. An alert lives in its query's."""
    if member.doctype == "Insights Alert":
        return member.query and frappe.db.get_value("Insights Query v3", member.query, "workbook")
    return member.get("workbook")


def is_member_share(share) -> bool:
    """Whether a DocShare has the one shape a share on a workbook member takes:
    a named person, reading a dashboard or chart, and nothing else.

    Write and share on a member are its workbook's. A query is read through
    its workbook or the chart over it, a folder or alert through its workbook
    alone. An org-wide row
    is the `Everyone` level's to say.
    """
    return (
        share.share_doctype in VISIBILITY_DOCTYPES
        and bool(share.user)
        and not share.everyone
        and not (share.write or share.share or share.submit)
    )


def validate_member_share(share, method=None):
    """A DocShare on a workbook member has the shape `is_member_share` names.

    `frappe.has_permission` asks a share after the controller refuses, so any
    other shape grants what the workbook does not. Refused where every share is
    written: `frappe.share`, the desk Share sidebar and a plain insert all save
    the row.
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
    """A row of a workbook member is written by the member's save, never on its own.

    `frappe.client.save` and `/api/resource` reach a
    child row by itself and ask only write on its parent, so every check the
    member makes on its rows - which charts a dashboard carries, who a level
    names, the standard guard - is skipped. The member's own save writes its
    rows without running their hooks, so a row whose hook runs is alone.

    frappe judges the parent it resolves `parenttype` to, case and trailing
    space ignored, and stores the string as sent, so the resolved name is asked.
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
    """Content is shareable with Insights users only, on every surface that shares it.

    A DocShare is a grant of the sharer's own access to a named person, and it
    carries down: a share on a dashboard reaches every chart on its grid and
    every query behind those, and `can_read_rows` reads it as a
    grant of this reader's own, which admits them to the rows and to the file.
    So who may be named is the app's rule and not the picker's contents.

    The picker cannot always show the person being named - an address typed by
    a user who may not look anyone up still has to land somewhere real.
    """
    if not emails:
        return

    # Administrator owns the workbooks an import creates and so stays on
    # the share list whenever one of them is re-shared
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
        # A level, or a dashboard carrying a chart, admits a reader to the
        # picture and not to the rows behind it. `can_read_rows` asks what is
        # left when both are taken away.
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

        # A preview render arrives as Guest carrying a key cut for one dashboard,
        # so the key is its whole grant. It reaches the documents the image it
        # produces already shows and stops there. The grant lives here rather
        # than on one endpoint because the render reads through the same
        # endpoints every other reader does.
        if ptype == "read" and is_being_previewed(doc.doctype, doc.name):
            return True

        # Whether there is a stored row, and who owns it, come from the row and
        # never from the document in hand. A whitelisted method runs on a
        # document built out of the request body - frappe's own
        # `/api/v2/method/run_doc_method` does exactly that - and `owner` and
        # `__islocal` are ordinary keys in it. Read off the copy, either one
        # hands the caller every chart on the site.
        #
        # `create` is the one question about a row that does not exist yet, and
        # the name column enforces that on its own: an insert onto a taken name
        # fails whatever this answers. A copy restored from a file carries the
        # names the file was written with, and those rows are still here.
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

        # a new member is judged on the workbook it names, as a stored one is
        workbook = is_new and doc.doctype in WORKBOOK_MEMBERS and workbook_of(doc)
        if workbook:
            docs = self._build_permission_query("Insights Workbook", access_type)
            return (
                docs.where(frappe.qb.DocType("Insights Workbook").name == workbook).limit(1).run(pluck="name")
            )

        # owning a member grants nothing: its workbook does
        if is_new or (is_owner and doc.doctype not in WORKBOOK_MEMBERS):
            return True

        docs = self._build_permission_query(doc.doctype, access_type)
        return docs.where(frappe.qb.DocType(doc.doctype).name == doc.name).limit(1).run(pluck="name")

    def get_granted(self, doctype, ptype="read") -> list[str]:
        """Names the user reaches through a grant.

        The admin bypass is left out, so an admin's list shows what was given to
        them, not every document on the site.
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
        """The members of `doctype` whose workbook grants `ptype`.

        The one source of write on a member, and of every grant on a folder or
        an alert: neither is drawn or shared, so a reader of the chart over a
        query reads no alert on it. Owning a member, a share on it or a team
        grant on it reads it and no more, so whoever the workbook no longer
        names keeps no edit through what they made there.
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
        """Returns a query to get docs whose declared visibility admits this user.

        Declared visibility is one grant source beside DocShare and
        the workbook/dashboard links. It is view-only: no level ever grants
        write or share, and no level consults the `Insights User` role.

        Under `ignore_visibility` no level admits anybody.
        """
        if ptype != "read" or doctype not in VISIBILITY_DOCTYPES or self.ignore_visibility:
            return None

        Content = frappe.qb.DocType(doctype)

        if self.user == "Guest":
            # a guest holds no role, so only the widest level reaches them
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
            named = (Content.visibility == ROLES) & NamedRoles.name.isnotnull()
            admits_user = admits_user | named

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

        # on site data desk admits a reader as well as a team grant does - the
        # rule `apply_user_permissions` reads rows by. Reading only: desk's read
        # is no grant to change the table's document
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
        """The documents of `doctype` a DocShare grants `ptype` on.

        A share names a person, and a guest is nobody. Frappe's own `get_shared`
        draws the line in the same place, and this module's own reading of an
        org-wide row is "every signed-in user". A guest is not signed in, so no
        share row is theirs - the `Public` visibility level is their whole grant.
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

        # a team grant on a dashboard reads it and no more
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

        # a team grant on a chart reads it and no more
        if ptype == "read":
            AllowedCharts = self._build_resource_query("Insights Chart v3")
            query = query.left_join(AllowedCharts).on(Chart.name == AllowedCharts.name)
            granted = granted | AllowedCharts.name.isnotnull()

        # A dashboard hands its readers the picture of every chart on it, as a
        # level does: read, and never write, delete or share, which would let
        # anyone who may save a dashboard act on a chart through it. Nor the
        # queries behind the chart, which `_named_grants` asks for.
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

        # A chart's grant carries read of the queries its pipeline reads in its
        # own workbook, and nothing else: never write or delete, which belong
        # to the workbook, and never to a reader a level or a dashboard alone
        # admits, who was published the picture and not the pipeline behind it.
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

        # and every query those queries source, however deep. See
        # `_queries_sourced_under_allowed_charts` for why the first hop is a
        # join and the rest is not.
        sourced = self._queries_sourced_under_allowed_charts
        if sourced:
            granted = granted | Query.name.isin(sorted(sourced))

        return query.where(granted)

    @cached_property
    def _named_grants(self):
        """This user's permissions with the grants of a picture taken away: the
        visibility levels, and a dashboard's grant on the charts it carries."""
        return self if self.ignore_visibility else InsightsPermissions(self.user, ignore_visibility=True)

    @cached_property
    def _queries_sourced_under_allowed_charts(self):
        """Every query below the ones the charts this user may read name directly.

        A chart's grant carries to the query behind it: reading the card is
        reading what that query returned. It has to carry as far as the engine
        reads, not one hop - `IbisQueryBuilder.check_query_reference` treats a
        saved reference as authorised, so the number on the card is already
        computed through the whole closure, and a bound that stopped at
        `Chart.query` refused the list of values in a column of it. It stops
        at the chart's own workbook, as the first hop does.

        Read from each query's own `operations`, never from the edge table: a
        background job rebuilds that after the save commits, and a grant that
        lags a write is a grant that refuses a dashboard its author just saved.

        Only the hops past the first are answered here. The first is a join and
        stays one: materialising the chart grant for every query in the graph
        is what makes a walk expensive. So the walk is seeded by the queries some other query
        actually sources, which is the only way to be more than one hop away,
        and a site with no layered queries pays one indexed scan and no join.
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
    user it runs as (`get_permission_user`).

    Through `may_read`, the one answer to "may this reader read this content".
    A reader admitted to a dashboard by its level can hold no Insights role at
    all, so frappe's role gate would refuse them a query the controller grants
    them through the very chart they are looking at.
    """
    if not can_read_referenced_query(query_name):
        frappe.throw(
            frappe._("You do not have access to a query this one references"),
            frappe.PermissionError,
        )


def can_read_referenced_query(query_name) -> bool:
    """The same question as an answer rather than as a refusal.

    A caller that has somewhere else to go asks it this way - a dashboard filter
    walks several links and takes the first one it may read, and throwing on the
    first unreadable one would refuse the filter for the links behind it.
    """
    from insights.permission_user import get_permission_user
    from insights.resolver import may_read

    # a name with no row resolves to nothing. The build says "not found" instead.
    if not frappe.db.exists("Insights Query v3", query_name):
        return True

    return bool(may_read(frappe.get_doc("Insights Query v3", query_name), get_permission_user()))


def can_read_chart(chart_name) -> bool:
    """Whether the caller may read a chart, asked the way a referenced query is.

    A chart authorises every query its stored pipeline reads for whoever may
    read the chart, so a surface bounded to that pipeline (`chart_reads`) asks
    this and not the query's own grant: a reader a level alone admits holds no
    grant on the query, and was still published what the chart draws from it.
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
    """Widening a document's reach is a share, not a write.

    `visibility` and `visible_to_roles` are ordinary fields, so the generic
    write surface reaches both. Widening either hands the owner's own read
    access to people who hold none of their own - a guest on the open internet,
    at the widest level - and that is what `share` means. So reach is checked
    where it is written, the same way a chart's query link is.

    Only a widening move is checked. Narrowing takes nothing away from anybody,
    and a reach that did not move leaves the document as saveable as the rest of
    it. A document that does not exist yet reaches nobody, so any level it
    arrives at is a widening - a copy is reset rather than admitted, see
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

    From `on_update`, so a save a later validator refuses sends nothing.
    """
    if (
        doc.visibility in OPEN_LEVELS
        and visibility_level(doc.visibility) > reach(doc.get_doc_before_save())[0]
    ):
        from insights.telemetry import capture_share_granted

        shared = "chart" if doc.doctype == "Insights Chart v3" else "dashboard"
        capture_share_granted(shared, "public" if doc.visibility == PUBLIC else "org", 1)


def refuse_unnameable_roles(added: set[str]) -> None:
    """A role every user holds is not a level, and `Roles` is not a way to say one."""
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
    """Settle `run_as_owner`: who may move it, what Public asks of it, and that a standard chart never ticks it.

    Only the owner or an admin ticks it: ticked, every read of the chart filters
    by a third person's permissions, and neither `share` nor write on a chart
    carries that. Any writer clears it, which hands nobody anybody's rows.

    Guests have no permissions of their own, so a chart reaching the Public
    level ticks it, and the untick is refused while the chart is Public or on a
    Public dashboard - the one place a guest read would otherwise draw an empty
    page. Each rule judges the move and never a row that already holds the
    state: `run_public_charts_as_owner` leaves it off where it cannot know whose
    rows to serve.

    A standard chart's owner is Administrator on every site, so ticked it would
    show every row to every reader of a chart the site did not write. A site
    that wants a number shown more widely ticks it on a copy.
    """
    # judged before Public ticks it below, which is not a move the caller made
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
    """Whether this save widens `doc`'s reach to readers nobody named one at a time.

    `Roles` is a publish as much as `Public` is: the owner's rows go out to
    everyone in the role exactly as they go out on a link.
    """
    return reaches_anybody(doc) and widens(doc.get_doc_before_save(), doc)


def check_owner_publishes(chart, through=None):
    """Only the owner sends the owner's rows to a reader nobody named.

    A chart with `run_as_owner` on serves every reader the owner's
    own rows. `share` cannot carry that move: it hands out the sharer's access
    and never a third person's, and write on a chart is not ownership of it -
    the same reason `validate_run_as_owner` leaves the tick to the owner. So the
    person whose rows go out is the one who may send them.

    One rule for the two writers that can widen a chart's reach: the chart's own
    save, and the save of a dashboard whose level `_build_chart_permission_query`
    turns into read on every chart placed on it. `through` is that dashboard,
    so the message names the document the caller was actually saving.

    Asked of the box and not of whose rows it serves today: an owner the
    workbook no longer names serves nobody their rows, and would serve them to
    this reach again when named back.
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
    """Whether this person may move `chart`'s box from where it is saved.

    Off, it moves on only for whoever `may_send_owner_rows`. On, it moves off
    for any writer. The share dialog enables its toggle by this answer, so the
    client holds no definition of admin of its own.
    """
    user = user or frappe.session.user
    saved = chart.name and frappe.db.get_value(chart.doctype, chart.name, "run_as_owner")
    if saved:
        return bool(frappe.has_permission(chart.doctype, ptype="write", doc=chart.name, user=user))
    return may_send_owner_rows(chart, user)


def may_send_owner_rows(chart, user: str | None = None) -> bool:
    """Whether this person may send `chart`'s owner's rows to its readers: its owner, or an admin."""
    user = user or frappe.session.user
    return user == chart.owner or is_admin(user)


def dashboard_linking_at(chart, levels: list[str], reader: str | None = None) -> str | None:
    """The title of a dashboard at one of `levels` that this chart is placed on.

    A chart's reach is not only its own level: the dashboard's readers get read
    on every chart on its grid, so a Private chart on a published dashboard is
    published. Two questions ask it - whether a guest is reading this chart
    (`validate_run_as_owner`), and what the share dialog's warning is
    about (`published_reach`) - and one query answers both.

    A title handed to a `reader` is that dashboard being read, so only the
    dashboards they may read answer them.
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
            # `Roles` naming no role admits nobody (`reach`)
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
    """How far this chart really reaches, for the screen that decides its box.

    Its own level is half the answer. The other half is the dashboards it is
    placed on: the widest of them publishes it whatever the chart says, and a
    chart at `Private` under a Public dashboard is the state
    `run_public_charts_as_owner` leaves behind. The share dialog's red confirm
    keys on this, or flipping the box on there sends the owner's rows out to
    everyone on that dashboard with nothing on screen saying so.
    """
    return {
        "published": reaches_anybody(chart),
        "published_by_dashboard": dashboard_linking_at(
            chart, VISIBILITY_LEVELS[VISIBILITY_LEVELS.index(ROLES) :], reader=frappe.session.user
        ),
        # `validate_run_as_owner` refuses the untick here, so the toggle
        # does not offer it
        "on_public_dashboard": bool(public_dashboards_linking(chart)),
    }


def check_dashboard_publishes(dashboard):
    """The same rule for the charts a published dashboard carries.

    `_build_chart_permission_query` hands the dashboard's readers read on every
    chart placed on it, without touching those charts' own level. So a dashboard
    at any level that reaches a population publishes them - `Roles` included,
    where the role names the readers and nobody named its members - and the
    dashboard's save is where that is settled.

    A guest has no permissions of their own, so a Public dashboard carries only
    charts that run as their owner. The box is the chart's declaration and only
    its owner checks it, so the publish is refused, naming the charts, and never
    ticks one. A chart that runs as its owner carries the owner's rows to the
    dashboard's readers, so `check_owner_publishes` asks the publisher.
    """
    if not reaches_anybody(dashboard):
        return

    runs_as_reader = []
    for name in charts_newly_published(dashboard):
        chart = frappe.get_doc("Insights Chart v3", name)

        # a shipped chart cannot be ticked (`validate_run_as_owner`), so
        # publishing it hands out nobody's rows
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
    """The linked charts this save carries to readers they did not have.

    A widening carries every chart on the grid. A reach that did not move
    carries only the charts the save added - adding a card to a published
    dashboard reaches the same readers, and the dashboard's save is the only
    save there is.

    Not every chart on every save: a save that moves neither the level nor the
    grid publishes nothing, and asking about the rest would refuse a layout edit
    on a dashboard somebody else's chart sits on - and would undo what
    `run_public_charts_as_owner` deliberately leaves unchecked.
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
    """A dashboard carries the charts of its own workbook that its author can read.

    `_build_chart_permission_query` grants read on every chart placed on a
    dashboard the caller can read, so naming a chart here is the same kind of
    grant. And the dashboard's filters narrow every chart on it, which is
    trusted to the chart's workbook and to nobody who merely reads the chart.

    Asked of the charts this save places, never of the ones already there: a
    chart's delete saves every dashboard showing it, and its deleter need not
    read the rest of somebody else's grid.
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
    """May this caller have more than the picture of `doc`?

    More is a breakdown, the rows behind a segment, the file, a card filter of
    their own, a page past the chart's `limit`, and the SQL and operations it
    ran as. The picture is the stored chart and its dashboard filters. Every
    surface that answers for a chart asks here - `insights.api.view`,
    `insights.api.authoring`, the chart's `fetch` and its drill.

    A level cannot answer it: it publishes a picture, and behind the picture
    are rows naming columns the card never drew.

    A guest gets the picture only. A chart run as its reader hands anyone else
    only their own rows. A chart run as its owner (`declared_owner`) answers by
    write: whoever may change what runs as the owner is trusted to act as them.
    Anything else answers by a grant that names this person: DocShare,
    workbook, team.

    Asked of the stored row: a whitelisted method's `self` is built from the
    request body. A name with no row is the caller's own unsaved pipeline.
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
    """May this person take data off the site as a file at all?

    About the person and never about a document: the site's own answer,
    `allow_download`, which an Insights Admin is not bound by, and the role's
    `export` permission, because taking data off the site is a role's business.
    This is what `get_user_info` publishes so a surface can offer the control.

    The role is asked about `Insights Query v3` - the doctype is this gate's own
    to name, or the same question answers differently depending on which surface
    reached it - and it is asked only of somebody an Insights role applies to.
    Every view endpoint is open to a reader holding none, and a DocShare is
    somebody deciding about them by name, so a ptype on a doctype whose roles
    they hold none of says nothing about them. Reading it as a refusal would
    conflate "holds no Insights role" with "holds one the site denied this".
    """
    user = user or frappe.session.user

    # a file is a bigger act than a page, and the page is already closed to them
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
    """May this person take *these* rows away as a file?

    Both halves, and a document is not optional, so no caller asks only the
    person's half. The second half is `can_read_rows`: a level publishes a picture, and the
    rows behind it are somebody's to decide about.
    """
    return can_download(user) and can_read_rows(doc, user or frappe.session.user)


def can_write(doc) -> bool:
    """Whether the caller may change `doc`: every surface that offers an edit asks here.

    The form's `read_only`, a view's `can_write` and the builder's author
    answer (`authoring.is_author`). Write on the document, an Insights role, and
    a site that may change its workbook: shipped content is read-only outside
    developer mode even to its owner, and `can_copy` is the affordance that
    replaces it.
    """
    from insights import standard

    workbook = doc.name if doc.doctype == "Insights Workbook" else workbook_of(doc)
    if standard.is_read_only(workbook):
        return False

    return bool(frappe.has_permission(doc.doctype, ptype="write", doc=doc)) and check_app_permission()


def can_share(doc) -> bool:
    """Whether the caller may widen who reads `doc` or name a person on it.

    What the builder offers Share by. On a workbook member share is write on
    its workbook today, so this answers as `can_write` does; asked separately
    so a workbook level that edits without sharing changes this answer alone.
    """
    return can_write(doc) and bool(frappe.has_permission(doc.doctype, ptype="share", doc=doc))


def check_app_permission(user=None):
    """The authoring gate: may this person enter the builder?

    It answers for the app, not for a document, and it is never consulted for
    viewing. `visibility` decides who reads a dashboard, and a view of it mounts
    for people who hold no Insights role at all. Editing is both questions at
    once - write rights on the document AND a role - and `can_write` is the one
    place that conjunction is made.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return True

    return any(role in INSIGHTS_ROLES for role in frappe.get_roles(user))


def check_trusted_code_author(documents) -> None:
    """Only an Insights Admin adds or changes trusted code (`trusted_code_of`).

    `documents` holds `(title, content, stored content)` for each query, chart or
    alert the caller brings, with nothing stored for a new one. Trusted code the
    stored document already carries keeps running and saving for whoever writes
    it; any other is refused, naming every document that brings some. Asked on a
    save, and before a file's or a copy's queries and charts go in, so one
    sentence names them all; and on a run - a build, an alert's send - which
    runs what is on screen unsaved.
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
    """The code in a query's operations, a chart's config or an alert's condition
    that an Insights Admin writes: a script, an expression that runs SQL, and a
    SQL query that calls a stored procedure.

    `Table.sql` and a procedure read any table on the connection without the
    reader's permissions, which is what a script may do and an expression or a
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
