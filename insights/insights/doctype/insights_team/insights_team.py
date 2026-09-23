# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import functools
import operator
from collections import Counter

import frappe
from frappe.core.doctype.role.role import get_users as get_users_with_role
from frappe.model.document import Document
from frappe.utils.caching import site_cache

from insights import user_permissions
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    exec_with_return,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    desk_reads_table,
    get_table_name,
    is_site_db,
)
from insights.not_permitted import refuse
from insights.telemetry import capture_share_granted

# the resource types a team grant may name, and the `object` each reports as
SHARED_OBJECT = {
    "Insights Data Source v3": "data_source",
    "Insights Table v3": "table",
    "Insights Dashboard v3": "dashboard",
    "Insights Chart v3": "chart",
}


class InsightsTeam(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from insights.insights.doctype.insights_resource_permission.insights_resource_permission import (
            InsightsResourcePermission,
        )
        from insights.insights.doctype.insights_team_member.insights_team_member import (
            InsightsTeamMember,
        )

        team_members: DF.Table[InsightsTeamMember]
        team_name: DF.Data
        team_permissions: DF.Table[InsightsResourcePermission]
    # end: auto-generated types

    def validate(self):
        if frappe.flags.in_migrate or frappe.flags.in_install:
            return

        if self.team_name == "Admin":
            if not self.team_members:
                frappe.throw("Admin team must have at least one member")
            if self.has_value_changed("team_name"):
                frappe.throw("Admin team name cannot be changed")

        for d in self.team_permissions:
            if d.resource_type not in SHARED_OBJECT:
                frappe.throw(f"Invalid resource type: {d.resource_type}")

    def on_trash(self):
        self.prevent_admin_team_deletion()
        clear_cache()

    def on_change(self):
        clear_cache()
        if self.team_name == "Admin" and self.has_value_changed("team_members"):
            self.set_admin_roles()
        self.capture_new_grants()

    def capture_new_grants(self):
        before = self.get_doc_before_save()
        held_before = set()
        if before:
            held_before = {(d.resource_type, d.resource_name) for d in before.team_permissions}

        granted = Counter(
            d.resource_type
            for d in self.team_permissions
            if (d.resource_type, d.resource_name) not in held_before
        )
        for resource_type, count in granted.items():
            capture_share_granted(SHARED_OBJECT[resource_type], "team", count)

    def prevent_admin_team_deletion(self):
        if self.team_name == "Admin":
            frappe.throw("Admin team cannot be deleted")

    def set_admin_roles(self):
        current_admins = get_users_with_role("Insights Admin")
        valid_admins = [m.user for m in self.team_members]

        invalid_admins = list(set(current_admins) - set(valid_admins))
        remove_admin_role(invalid_admins)

        current_admins = list(set(current_admins) - set(invalid_admins))
        new_admins = list(set(valid_admins) - set(current_admins))
        give_admin_role(new_admins)

    def get_members(self):
        return frappe.get_all(
            "User",
            filters={"name": ["in", [m.user for m in self.team_members]]},
            fields=["full_name", "email", "user_image", "name"],
        )

    def get_sources(self):
        return [
            d.resource_name for d in self.team_permissions if d.resource_type == "Insights Data Source v3"
        ]

    def get_tables(self):
        return [d.resource_name for d in self.team_permissions if d.resource_type == "Insights Table v3"]

    def get_allowed_resources(self, resource_type):
        if not self.team_permissions:
            return []
        if resource_type == "Insights Data Source v3":
            return self.get_allowed_sources()
        elif resource_type == "Insights Table v3":
            return self.get_allowed_tables()
        else:
            return []

    def get_allowed_sources(self):
        allowed_sources = self.get_sources()
        sources_of_allowed_tables = frappe.get_all(
            "Insights Table v3",
            filters={"name": ["in", self.get_tables()]},
            pluck="data_source",
            distinct=True,
        )
        return list(set(allowed_sources + sources_of_allowed_tables))

    def get_allowed_tables(self):
        allowed_sources = self.get_sources()
        allowed_tables = self.get_tables()

        sources_of_allowed_tables = frappe.get_all(
            "Insights Table v3",
            filters={"name": ["in", allowed_tables]},
            pluck="data_source",
            distinct=True,
        )

        unrestricted_sources = list(set(allowed_sources) - set(sources_of_allowed_tables))
        allowed_tables_of_unrestricted_sources = frappe.get_all(
            "Insights Table v3",
            filters={"data_source": ["in", unrestricted_sources]},
            pluck="name",
        )

        return list(set(allowed_tables + allowed_tables_of_unrestricted_sources))


def update_admin_team(user, method=None):
    try:
        if not user.has_value_changed("roles"):
            return

        roles = user.get("roles", [])
        is_user = next((True for role in roles if role.role == "Insights User"), False)
        is_admin = next((True for role in roles if role.role == "Insights Admin"), False)
        if not is_user and not is_admin:
            return

        admin_members = admin_team_members()
        if not is_admin and user.name in admin_members:
            clear_cache()
            frappe.db.delete(
                "Insights Team Member",
                {
                    "parent": "Admin",
                    "user": user.name,
                },
            )
        if is_admin and user.name not in admin_team_members():
            team = frappe.get_cached_doc("Insights Team", "Admin")
            team.append("team_members", {"user": user.name})
            team.save(ignore_permissions=True)

    except Exception:
        frappe.log_error(title="update_admin_team")


def clear_cache():
    get_teams.clear_cache()
    admin_team_members.clear_cache()
    _get_allowed_resources_for_user.clear_cache()


@site_cache(ttl=60 * 60 * 24)
def get_teams(user):
    Team = frappe.qb.DocType("Insights Team")
    TeamMember = frappe.qb.DocType("Insights Team Member")
    return (
        frappe.qb.from_(Team)
        .select(Team.name)
        .distinct()
        .join(TeamMember)
        .on(Team.name == TeamMember.parent)
        .where(TeamMember.user == user)
        .run(pluck=True)
    ) or []


@site_cache(ttl=60 * 60 * 24)
def admin_team_members():
    return frappe.get_all(
        "Insights Team Member",
        filters={"parent": "Admin"},
        pluck="user",
    )


def is_admin(user):
    return (
        user == "Administrator" or user in admin_team_members() or "System Manager" in frappe.get_roles(user)
    )


def get_allowed_resources_for_user(resource_type, user=None):
    user = user or frappe.session.user
    return _get_allowed_resources_for_user(resource_type, user)


@site_cache(ttl=60 * 60 * 24)
def _get_allowed_resources_for_user(resource_type, user):
    permsisions_disabled = not frappe.db.get_single_value("Insights Settings", "enable_permissions")
    if permsisions_disabled or is_admin(user):
        return frappe.get_all(resource_type, pluck="name")

    teams = get_teams(user)
    if not teams:
        return []

    resources = []
    for team in teams:
        team = frappe.get_cached_doc("Insights Team", team)
        resources.extend(team.get_allowed_resources(resource_type))

    return list(set(resources))


# not used anymore in v3
# the permissions are enforced from permissions.py:get_*_query_conditions
def get_permission_filter(resource_type, user=None):
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return {}

    user = user or frappe.session.user
    if is_admin(user):
        return {}

    allowed_resource = get_allowed_resources_for_user(resource_type, user)
    if not allowed_resource:
        return {"name": ["is", "not set"]}
    return {"name": ["in", allowed_resource]}


def check_data_source_permission(source_name, user=None, raise_error=True):
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return True

    user = user or frappe.session.user
    if is_admin(user):
        return True

    allowed_sources = get_allowed_resources_for_user("Insights Data Source v3", user)

    if source_name not in allowed_sources:
        if raise_error:
            refuse(message=frappe._("You do not have permission to access this data source"))
        else:
            return False

    return True


def check_table_permission(data_source, table, user=None, raise_error=True):
    """Whether this user may read this table, refused the one way the app refuses.

    On site data desk's own permissions admit a reader as well as a team
    grant does - the most permissive of the two - and an admin's pass through
    the team gate is no grant there. Elsewhere only a team grant can, and an
    admin passes.

    `NotPermitted` is the type the refusal contract catches (`answers_refusal`),
    and a team grant refuses the same idea every other check here refuses: this
    reader may not read this data.
    """
    # permissions imports this module
    from insights.permissions import check_app_permission

    user = user or frappe.session.user
    if is_site_db(data_source):
        permitted = desk_reads_table(table, user) or team_grant(data_source, table, user) is not None
    elif is_admin(user):
        permitted = True
    elif not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        # every Insights user, and not a guest or a session holding no Insights role
        permitted = check_app_permission(user)
    else:
        permitted = get_table_name(data_source, table) in get_allowed_resources_for_user(
            "Insights Table v3", user
        )

    if not permitted:
        if raise_error:
            refuse(message=frappe._("You do not have permission to access this table"))
        return False

    return True


def team_grant(data_source, table, user=None) -> list[str] | None:
    """The Table Restrictions a team grant reads this table under, any one of them enough.

    Empty is the whole table, and nothing is no grant at all. Only a team that
    names the table or its source grants it - an admin's pass through the team
    gate is not a grant, so on site data an admin reads what desk gives them.
    Each team grants the rows its own restrictions allow, and one team's grant
    never narrows another's: a team that grants without a restriction grants
    the whole table.
    """
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return None

    user = user or frappe.session.user
    if is_admin(user):
        return None

    table_name = get_table_name(data_source, table)
    restrictions = None
    for team in get_teams(user):
        team = frappe.get_cached_doc("Insights Team", team)
        if table_name not in team.get_allowed_resources("Insights Table v3"):
            continue
        rows = [
            row.table_restrictions
            for row in team.team_permissions
            if row.resource_type == "Insights Table v3" and row.resource_name == table_name
        ]
        if not rows or not all(rows):
            return []
        restrictions = [*(restrictions or []), *rows]

    return restrictions


def apply_table_restrictions(table, data_source, table_name, user=None):
    granted = team_grant(data_source, table_name, user=user)
    if not granted:
        return table

    user_permissions.record_narrowed(user or frappe.session.user)
    return table.filter(restriction_predicate(table, granted))


def restriction_predicate(table, restrictions: list[str]):
    """The Table Restrictions as one condition over `table`'s own columns, any one of them enough."""
    columns = {column: table[column] for column in table.schema().names}
    predicates = [exec_with_return(expression.strip(), columns) for expression in restrictions]
    return functools.reduce(operator.or_, predicates)


def remove_admin_role(users):
    for user in users:
        frappe.db.delete(
            "Has Role",
            {
                "parent": user,
                "parenttype": "User",
                "role": "Insights Admin",
            },
        )


def give_admin_role(users):
    for user in users:
        if not has_admin_role(user):
            u = frappe.get_doc("User", user)
            u.add_roles("Insights Admin")


def has_admin_role(user):
    return frappe.db.exists(
        "Has Role",
        {
            "parent": user,
            "parenttype": "User",
            "role": "Insights Admin",
        },
    )
