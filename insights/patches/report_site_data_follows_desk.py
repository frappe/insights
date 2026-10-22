"""List who reads site data differently now that desk alone decides it.

Insights before 3.50 let a reader into a site table through a team, then filtered the
rows by desk permissions unless Apply User Permissions was off, and narrowed
them further by the team's Table Restriction. Now desk decides alone, so:

- a reader whom a team let in, but whom desk does not let read the doctype,
  gets Not Permitted. With Apply User Permissions on they saw no rows before;
  with it off, every row.
- with Apply User Permissions off, a reader whom desk lets read the doctype
  now gets only desk's rows and columns.
- a Table Restriction on a site table stops applying, so its team reads every
  row desk gives them.

Each finding becomes an upgrade item for the admins.
"""

import re

import frappe
from frappe.model import no_value_fields
from frappe.utils import cint

from insights.upgrade import add_item

CODE = "P17"
SETTINGS = "Insights Settings"
DATA_SOURCE = "Insights Data Source v3"
TABLE = "Insights Table v3"
TEAM = "Insights Team"
INSIGHTS_ROLES = ("Insights User", "Insights Admin")
# a restriction that keeps the rows whose one field holds one value
FIELD_EQUALS = re.compile(r"""^(\w+)\s*==\s*(?:'([^']*)'|"([^"]*)")$""")


def execute():
    found = site_data_findings()
    for user in found.users:
        data = {"user": user.user, "doctypes": user.unreadable, "narrowed": user.narrowed}
        add_item(CODE, user_message(data), reference=("User", user.user), data=data)
    for team in found.restrictions:
        data = {
            "team": team.team,
            "members": team.users,
            "restrictions": [restriction_data(r.doctype, r.restriction) for r in team.restrictions],
        }
        add_item(CODE, restriction_message(data), reference=(TEAM, team.team), data=data)


def site_data_findings() -> frappe._dict:
    """Who reads site data differently on this site than Insights before 3.50 let them.

    `users` has one entry per reader: `unreadable`, the doctypes a team let
    them into that desk does not let them read, and `narrowed`, the doctypes
    whose rows or columns desk now narrows for them. `restrictions` has one
    entry per team with a Table Restriction on a site table: the
    `restrictions` that stopped applying and the `users` they applied to.

    Read Apply User Permissions before `retire_site_apply_user_permissions`
    deletes it. A missing row means off, as Insights before 3.50 read it.
    """
    from insights.insights.doctype.insights_team.insights_team import clear_cache

    clear_cache()
    team_permissions = cint(frappe.db.get_single_value(SETTINGS, "enable_permissions"))
    applied = frappe.db.get_value(
        "Singles", {"doctype": SETTINGS, "field": "apply_user_permissions"}, "value", order_by=None
    )
    desk_filtered = bool(cint(applied))

    site_sources = frappe.get_all(DATA_SOURCE, filters={"is_site_db": 1}, pluck="name")
    used = used_site_tables(site_sources)

    users = []
    for user in insights_users():
        reached = reached_tables(user, used)
        unreadable, narrowed = set(), set()
        for table in reached:
            denied = desk_denies(table, user)
            if denied:
                unreadable.update(denied)
            elif not desk_filtered and desk_narrows(table, user):
                narrowed.add(table.removeprefix("tab"))
        if unreadable or narrowed:
            users.append(frappe._dict(user=user, unreadable=sorted(unreadable), narrowed=sorted(narrowed)))

    return frappe._dict(
        users=users,
        restrictions=site_restrictions(site_sources) if team_permissions else [],
    )


def used_site_tables(site_sources: list[str]) -> dict[str, str]:
    """The site tables a saved query reads, by the name of their Insights Table."""
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
    from insights.insights.query_utils import table_references

    used = {}
    for operations in frappe.get_all("Insights Query v3", pluck="operations"):
        for ref in table_references(operations):
            if ref["data_source"] in site_sources:
                used[get_table_name(ref["data_source"], ref["table_name"])] = ref["table_name"]
    return used


def insights_users() -> list[str]:
    """The enabled users who could open Insights before 3.50. Administrator reads every doctype."""
    holders = frappe.get_all(
        "Has Role",
        filters={"parenttype": "User", "role": ("in", INSIGHTS_ROLES)},
        pluck="parent",
        distinct=True,
    )
    return frappe.get_all(
        "User",
        filters=[["name", "in", holders or [""]], ["name", "!=", "Administrator"], ["enabled", "=", 1]],
        pluck="name",
        order_by="name asc",
    )


def reached_tables(user: str, used: dict[str, str]) -> list[str]:
    """The used site tables Insights before 3.50 let `user` into: every table with team
    permissions off or for an admin, else the tables their teams grant."""
    from insights.insights.doctype.insights_team.insights_team import get_allowed_resources_for_user

    allowed = set(get_allowed_resources_for_user(TABLE, user))
    return sorted(table for name, table in used.items() if name in allowed)


def desk_denies(table: str, user: str) -> list[str]:
    """The doctypes desk would have to let `user` read for them to read `table`."""
    from insights import not_permitted
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import strip_schema_prefix

    table = strip_schema_prefix(table)
    if table == "tabSingles":
        return []
    try:
        return not_permitted.unreadable_doctypes(table, user)
    except frappe.DoesNotExistError:
        return [table.removeprefix("tab")]


def desk_narrows(table: str, user: str) -> bool:
    """Whether desk gives `user` fewer than all rows or columns of `table`."""
    from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
        _has_where_clause,
        get_permission_query_for_table,
        get_permitted_columns_for_table,
        strip_schema_prefix,
    )

    table = strip_schema_prefix(table)
    if table == "tabSingles":
        return False
    query = get_permission_query_for_table(table, user)
    if query and _has_where_clause(query):
        return True
    meta = frappe.get_meta(table.removeprefix("tab"))
    columns = {df.fieldname for df in meta.fields if df.fieldtype not in no_value_fields}
    return bool(columns - get_permitted_columns_for_table(table, user))


def site_restrictions(site_sources: list[str]) -> list[frappe._dict]:
    """Each team's Table Restrictions on site tables, with the members they narrowed."""
    rows = frappe.get_all(
        "Insights Resource Permission",
        filters={
            "parenttype": TEAM,
            "resource_type": TABLE,
            "table_restrictions": ("is", "set"),
        },
        fields=["parent", "resource_name", "table_restrictions"],
        order_by="parent asc, idx asc",
    )
    teams: dict[str, frappe._dict] = {}
    for row in rows:
        table = frappe.db.get_value(TABLE, row.resource_name, ["data_source", "table"], as_dict=True)
        if not table or table.data_source not in site_sources:
            continue
        team = teams.setdefault(row.parent, frappe._dict(team=row.parent, restrictions=[], users=[]))
        team.restrictions.append(
            frappe._dict(doctype=table.table.removeprefix("tab"), restriction=row.table_restrictions.strip())
        )

    for team in teams.values():
        members = frappe.get_all(
            "Insights Team Member", filters={"parent": team.team}, pluck="user", order_by="user asc"
        )
        team.users = frappe.get_all(
            "User", filters={"name": ("in", members or [""]), "enabled": 1}, pluck="name", order_by="name asc"
        )
    return list(teams.values())


def restriction_data(doctype: str, condition: str) -> dict:
    """A restriction, with the field and value it compares when it is that simple."""
    data = {"doctype": doctype, "condition": condition}
    if match := FIELD_EQUALS.match(condition):
        field, single, double = match.groups()
        data.update(field=field, value=double if single is None else single)
    return data


def user_message(data: dict) -> str:
    parts = []
    if data["doctypes"]:
        parts.append(f"charts on {', '.join(data['doctypes'])} say Not Permitted")
    if data["narrowed"]:
        parts.append(f"reads only the rows desk gives them of {', '.join(data['narrowed'])}")
    return f"{data['user']}: {'; '.join(parts)}"


def restriction_message(data: dict) -> str:
    restrictions = ", ".join(f"{r['doctype']} `{r['condition']}`" for r in data["restrictions"])
    members = ", ".join(data["members"]) or "no members"
    return f'Team "{data["team"]}" ({members}): {restrictions}'
