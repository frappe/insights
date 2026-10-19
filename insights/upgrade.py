"""What the upgrade from Insights 3 could not carry over, and who used Insights 3.

A patch that cannot carry something over records it with `add_item`. The
upgrade dialog lists the items, and opens once for each user who used
Insights 3.
"""

import frappe

ITEM = "Insights Upgrade Item"
# a user default, so it is per user and survives a cache clear
SEEN_VERSION = "insights_seen_version"
INSIGHTS_ROLES = ("Insights User", "Insights Admin")


def add_item(
    code: str,
    message: str,
    reference: tuple[str, str] | None = None,
    user: str | None = None,
    action: str | None = None,
):
    """Record what the upgrade could not carry over.

    `reference` is a `(doctype, name)` pair. `user` is the person it concerns;
    without one it is for admins. A patch that runs again adds no second item,
    and does not bring back one a user dismissed.
    """
    reference_doctype, reference_name = reference or (None, None)
    key = {
        "code": code,
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "user": user,
    }
    if frappe.db.exists(ITEM, {field: value or ("is", "not set") for field, value in key.items()}):
        return
    frappe.get_doc({"doctype": ITEM, **key, "message": message, "action": action}).insert(
        ignore_permissions=True
    )


def was_on_v3() -> bool:
    """Whether this migrate is the upgrade from a release of Insights 3.

    Read during patches: frappe writes the new version into Installed
    Application after them. A develop build said 3.x until it became 4.0.0-dev,
    and never ran the Insights 3 that users are welcomed from.
    """
    row = frappe.db.get_value(
        "Installed Application",
        {"parent": "Installed Applications", "app_name": "insights"},
        ["app_version", "git_branch"],
        as_dict=True,
    )
    return bool(row) and (row.app_version or "").startswith("3.") and row.git_branch != "develop"


def mark_v3_users():
    """Mark everyone who could use Insights at migrate time as an Insights 3 user.

    A new site never runs it: installing an app marks its patches done.
    """
    users = frappe.get_all(
        "Has Role",
        filters={"parenttype": "User", "role": ("in", INSIGHTS_ROLES)},
        pluck="parent",
        distinct=True,
    )
    # holds every role without a Has Role row for it
    for user in {*users, "Administrator"}:
        frappe.defaults.set_user_default(SEEN_VERSION, "3", user)


def upgraded_from_v3(user: str | None = None) -> bool:
    return frappe.defaults.get_user_default(SEEN_VERSION, user) == "3"


def mark_seen(user: str | None = None):
    frappe.defaults.set_user_default(SEEN_VERSION, "4", user)


def open_item_filters(user: str | None = None) -> dict:
    """An admin works through every open item, anyone else through their own.
    The admins are the roles the doctype lets read every item."""
    user = user or frappe.session.user
    filters = {"status": "Open"}
    if not {"Insights Admin", "System Manager"} & set(frappe.get_roles(user)):
        filters["user"] = user
    return filters


def get_item(name: str):
    """The open item `name`, if the session user may work on it."""
    filters = {**open_item_filters(), "name": name}
    if not frappe.db.exists(ITEM, filters):
        frappe.throw(frappe._("This upgrade item is not open to you."), frappe.PermissionError)
    return frappe.get_doc(ITEM, name)
