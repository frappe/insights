import frappe
from frappe.query_builder.functions import IfNull
from frappe.share import add_docshare

from insights.permissions import get_insights_users
from insights.upgrade import add_item

WORKBOOK = "Insights Workbook"
QUERY = "Insights Query v3"
ALERT = "Insights Alert"
# Insights 3 let the owner of each of these edit it, whatever the workbook allowed
OWNED_MEMBERS = (QUERY, "Insights Chart v3", "Insights Dashboard v3")


def execute():
    """Share each workbook with the owners of its members who cannot edit it.

    Insights 3 let an owner edit what they made. Insights 4 gives access through
    the workbook only, so an owner the workbook does not name loses edit, and
    read too unless a share gives it. A user who is not an Insights user, or is
    disabled, could not open Insights 3 either, and is skipped.
    """
    users = get_insights_users()
    shared = {}
    for workbook, owner in member_owners():
        if owner not in users or not frappe.db.exists(WORKBOOK, workbook):
            continue
        if frappe.has_permission(WORKBOOK, "write", doc=workbook, user=owner):
            continue
        share_workbook(workbook, owner, write=1)
        shared.setdefault(workbook, []).append(owner)

    for workbook, owners in shared.items():
        add_item(
            "P3",
            f'"{workbook_title(workbook)}": {", ".join(owners)} can now edit it',
            reference=(WORKBOOK, workbook),
        )


def member_owners() -> list[tuple[str, str]]:
    """Every (workbook, owner) pair of the workbook's members, an alert counted
    in its query's workbook."""
    pairs = set()
    for doctype in OWNED_MEMBERS:
        pairs.update(
            frappe.get_all(
                doctype,
                filters={"workbook": ("is", "set")},
                fields=["workbook", "owner"],
                distinct=True,
                as_list=True,
            )
        )
    Alert = frappe.qb.DocType(ALERT)
    Query = frappe.qb.DocType(QUERY)
    pairs.update(
        frappe.qb.from_(Alert)
        .join(Query)
        .on(Query.name == Alert.query)
        .select(Query.workbook, Alert.owner)
        .where(IfNull(Query.workbook, "") != "")
        .distinct()
        .run()
    )
    return sorted(pairs)


def share_workbook(workbook: str, user: str, write: int = 0, share: int = 0) -> bool:
    """Share `workbook` with `user`, never taking away a flag a share already
    gives. Answers whether anything changed."""
    existing = frappe.db.get_value(
        "DocShare",
        {"share_doctype": WORKBOOK, "share_name": workbook, "user": user, "everyone": 0},
        ["write", "share"],
        as_dict=True,
    )
    if existing and existing.write >= write and existing.share >= share:
        return False
    add_docshare(
        WORKBOOK,
        workbook,
        user=user,
        write=max(write, existing.write if existing else 0),
        share=max(share, existing.share if existing else 0),
        flags={"ignore_share_permission": True},
        notify=0,
    )
    return True


def workbook_title(workbook: str) -> str:
    return frappe.db.get_value(WORKBOOK, workbook, "title") or workbook
