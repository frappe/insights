"""What the upgrade to Insights 3.50 could not carry over, and who used an earlier release.

A patch that cannot carry something over records it with `add_item`. The
upgrade dialog lists the items, and opens once for each user who used an
earlier release.
"""

import frappe
from semantic_version import Version

ITEM = "Insights Upgrade Item"
# a user default, so it is per user and survives a cache clear
SEEN_VERSION = "insights_seen_version"
INSIGHTS_ROLES = ("Insights User", "Insights Admin")
WORKBOOK = "Insights Workbook"
# The template folders before 3.50, and the standard workbook that replaces each
TEMPLATE_WORKBOOKS = {"accounting": "accounts", "purchasing": "buying", "sales": "selling", "stock": "stock"}


def add_item(
    code: str,
    message: str,
    reference: tuple[str, str] | None = None,
    user: str | None = None,
    action: str | None = None,
    data: dict | None = None,
):
    """Record what the upgrade could not carry over.

    `reference` is a `(doctype, name)` pair. `user` is the person it concerns;
    without one it is for admins. `data` holds the names and values the item's
    sentence shows, by key: users as user ids, documents by title. A patch that
    runs again adds no second item, and does not bring back one a user dismissed.
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
    frappe.get_doc({"doctype": ITEM, **key, "message": message, "action": action, "data": data or {}}).insert(
        ignore_permissions=True
    )


def was_on_v3() -> bool:
    """Whether this migrate is the upgrade from a release before 3.50.

    Read during patches: frappe writes the new version into Installed
    Application after them. A develop build said 3.x for a while, and never ran
    the release that users are welcomed from.
    """
    row = frappe.db.get_value(
        "Installed Application",
        {"parent": "Installed Applications", "app_name": "insights"},
        ["app_version", "git_branch"],
        as_dict=True,
    )
    if not row or row.git_branch == "develop":
        return False
    try:
        version = Version.coerce(row.app_version or "")
    except ValueError:
        return False  # nosemgrep - a version that does not parse names no release before 3.50
    return (version.major, version.minor) < (3, 50)


def mark_v3_users():
    """Mark everyone who could use Insights at migrate time as a user of Insights before 3.50.

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
    frappe.defaults.set_user_default(SEEN_VERSION, "3.50", user)


def is_upgrade_admin(user: str | None = None) -> bool:
    """Whether `user` holds a role the doctype lets read every item."""
    return bool({"Insights Admin", "System Manager"} & set(frappe.get_roles(user or frappe.session.user)))


def item_filters(user: str | None = None) -> dict:
    """The items `user` works through: an admin every item, anyone else their own."""
    user = user or frappe.session.user
    return {} if is_upgrade_admin(user) else {"user": user}


def get_item(name: str):
    """The open item `name`, if the session user may work on it."""
    filters = {**item_filters(), "status": "Open", "name": name}
    if not frappe.db.exists(ITEM, filters):
        frappe.throw(frappe._("This upgrade item is not open to you."), frappe.PermissionError)
    return frappe.get_doc(ITEM, name)


def template_copies(template: str | None = None) -> list[frappe._dict]:
    """The workbooks made from an old Insights template, or from `template`
    (`app/folder`), oldest first.

    Insights before 3.50 recorded the template in `from_template`, and earlier releases
    only its folder. The field is gone, and its column stays.
    """
    if not frappe.db.has_column(WORKBOOK, "from_template"):
        return []
    table = frappe.qb.DocType(WORKBOOK)
    query = (
        frappe.qb.from_(table)
        .select(table.name, table.title, table.from_template)
        .where(table.from_template.isnotnull() & (table.from_template != ""))
        .orderby(table.creation)
    )
    if frappe.db.has_column(WORKBOOK, "imported_checksum"):
        query = query.select(table.imported_checksum)
    if template:
        query = query.where(table.from_template.isin([template, template.rpartition("/")[2]]))
    return query.run(as_dict=True)


def standard_workbook_of(template: str) -> str | None:
    """The standard workbook that replaces the old Insights template `template`."""
    return TEMPLATE_WORKBOOKS.get(template.rpartition("/")[2])
