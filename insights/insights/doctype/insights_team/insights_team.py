# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.core.doctype.role.role import get_users as get_users_with_role
from frappe.model.document import Document
from frappe.utils.caching import site_cache
from ibis import _

from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    exec_with_return,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name


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
            if d.resource_type not in [
                "Insights Data Source v3",
                "Insights Table v3",
            ]:
                frappe.throw(f"Invalid resource type: {d.resource_type}")

    def on_trash(self):
        self.prevent_admin_team_deletion()
        clear_cache()

    def on_change(self):
        clear_cache()
        if self.team_name == "Admin" and self.has_value_changed("team_members"):
            self.set_admin_roles()

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
            d.resource_name
            for d in self.team_permissions
            if d.resource_type == "Insights Data Source v3"
        ]

    def get_tables(self):
        return [
            d.resource_name
            for d in self.team_permissions
            if d.resource_type == "Insights Table v3"
        ]

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

        unrestricted_sources = list(
            set(allowed_sources) - set(sources_of_allowed_tables)
        )
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
        is_admin = next(
            (True for role in roles if role.role == "Insights Admin"), False
        )
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
    return user == "Administrator" or user in admin_team_members()


def get_allowed_resources_for_user(resource_type, user=None):
    user = user or frappe.session.user
    return _get_allowed_resources_for_user(resource_type, user)


@site_cache(ttl=60 * 60 * 24)
def _get_allowed_resources_for_user(resource_type, user):
    permsisions_disabled = not frappe.db.get_single_value(
        "Insights Settings", "enable_permissions"
    )
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
            frappe.throw(
                "You do not have permission to access this data source",
                exc=frappe.PermissionError,
            )
        else:
            return False

    return True


def check_table_permission(data_source, table, user=None, raise_error=True):
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return True

    user = user or frappe.session.user
    if is_admin(user):
        return True

    table_name = get_table_name(data_source, table)
    allowed_tables = get_allowed_resources_for_user("Insights Table v3", user)

    if table_name not in allowed_tables:
        if raise_error:
            frappe.throw(
                "You do not have permission to access this table",
                exc=frappe.PermissionError,
            )
        else:
            return False

    return True


def get_table_restrictions(data_source, table, user=None):
    if not frappe.db.get_single_value("Insights Settings", "enable_permissions"):
        return []

    user = user or frappe.session.user
    if is_admin(user):
        return []

    table_name = get_table_name(data_source, table)
    table_restrictions = frappe.get_all(
        "Insights Resource Permission",
        filters={
            "parent": ["in", get_teams(user)],
            "resource_name": table_name,
            "resource_type": "Insights Table v3",
            "table_restrictions": ["is", "set"],
        },
        pluck="table_restrictions",
    )
    return table_restrictions


def apply_table_restrictions(table, data_source, table_name):
    restrictions = get_table_restrictions(data_source, table_name)
    if not restrictions:
        return table

    filters = restrictions
    table_columns = table.schema().names
    table_columns_dict = {column: getattr(_, column) for column in table_columns}
    for filter_expression in filters:
        filter_expression = filter_expression.strip()
        table = table.filter(exec_with_return(filter_expression, table_columns_dict))

    return table


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
