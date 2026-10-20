import frappe

from insights import standard
from insights.decorators import insights_whitelist
from insights.upgrade import (
    ITEM,
    WORKBOOK,
    get_item,
    mark_seen,
    open_item_filters,
    standard_workbook_of,
    template_copies,
)


@insights_whitelist()
def get_upgrade_items():
    items = frappe.get_all(
        ITEM,
        filters=open_item_filters(),
        fields=["name", "code", "message", "data", "reference_doctype", "reference_name", "user", "action"],
        order_by="code asc, creation asc",
    )
    # an app uninstalled since the upgrade took the doctype an item names
    gone = {
        doctype
        for doctype in {item.reference_doctype for item in items if item.reference_doctype}
        if not frappe.db.exists("DocType", doctype)
    }
    items = [item for item in items if item.reference_doctype not in gone]
    for item in items:
        item.data = frappe.parse_json(item.data) or {}
    people = names_of_users({value for item in items for value in strings_in(item.data)})
    for item in items:
        item.workbook = reference_workbook(item)
        item.form_url = form_url(item)
        item.can_fix = can_fix(item)
        item.people = {value: people[value] for value in strings_in(item.data) if value in people}
    return items


def strings_in(data: dict) -> set[str]:
    """The strings of an item's data: its values, and those in its lists and
    in the dicts they hold."""
    found = set()
    for value in data.values():
        for entry in value if isinstance(value, list) else [value]:
            for string in entry.values() if isinstance(entry, dict) else [entry]:
                if isinstance(string, str):
                    found.add(string)
    return found


def names_of_users(values: set[str]) -> dict[str, dict]:
    """The full and first name of each of `values` that is a user."""
    users = (
        frappe.get_all(
            "User", filters={"name": ("in", list(values))}, fields=["name", "full_name", "first_name"]
        )
        if values
        else []
    )
    return {
        user.name: {
            "full_name": user.full_name or user.name,
            "first_name": user.first_name or user.full_name or user.name,
        }
        for user in users
    }


def form_url(item) -> str | None:
    """The desk form of a reference the app has no page for, such as a user."""
    if (
        item.workbook
        or not item.reference_name
        or not frappe.db.exists(item.reference_doctype, item.reference_name)
    ):
        return None
    return frappe.utils.get_url_to_form(item.reference_doctype, item.reference_name)


def can_fix(item) -> bool:
    """Whether the session user holds the permission the item's fix needs."""
    if item.action == "open_settings":
        return bool(frappe.has_permission("Insights Settings", "write"))
    if item.action == "delete_workbook":
        return bool(frappe.has_permission("Insights Workbook", "delete", doc=item.reference_name))
    return False


def reference_workbook(item) -> str | None:
    """The workbook the app opens the reference in: a query, chart or dashboard
    has its own route under its workbook."""
    if item.reference_doctype == "Insights Workbook":
        return item.reference_name
    if item.reference_doctype and frappe.get_meta(item.reference_doctype).has_field("workbook"):
        return frappe.db.get_value(item.reference_doctype, item.reference_name, "workbook")


@insights_whitelist(methods=["POST"])
def mark_upgrade_seen():
    mark_seen()


@insights_whitelist(methods=["POST"])
def dismiss_upgrade_items(names: list[str]) -> list[str]:
    """Dismiss each of `names` still open to the session user, and return them.
    Another admin or another tab may have closed some already, which leaves
    nothing to do for those."""
    names = frappe.get_all(ITEM, filters={**open_item_filters(), "name": ("in", names)}, pluck="name")
    for name in names:
        frappe.db.set_value(ITEM, name, "status", "Dismissed")
    return names


@insights_whitelist(methods=["POST"])
def fix_upgrade_item(name: str):
    """Apply the item's fix with the session user's own permission on its reference."""
    item = get_item(name)
    if item.action == "delete_workbook":
        # checks the session user may delete the workbook
        frappe.delete_doc("Insights Workbook", item.reference_name)
    else:
        frappe.throw(frappe._("This item has no fix to apply."))
    # a save would check the reference, which the fix may have deleted
    item.db_set("status", "Done")


@insights_whitelist()
def get_shipping_apps() -> list[dict]:
    """Each app that ships workbooks, by the title and logo the workbook list
    shows it with. The wizard's welcome pictures the dashboards they ship to a
    reader who may open none of them."""
    workbooks = frappe.get_all(WORKBOOK, filters={"is_standard": 1}, pluck="name")
    return [
        {"app": app, "title": standard.app_title(app), "logo": standard.app_logo_url(app)}
        for app in sorted(set(standard.shipping_apps(workbooks).values()))
    ]


@insights_whitelist()
def get_template_workbook(template: str) -> str | None:
    """The workbook an Insights 3 template link opens: the site's copy of
    `template`, else the standard workbook that replaced it, if the user may
    read it."""
    names = [copy.name for copy in template_copies(template)]
    names.append(standard_workbook_of(template))
    return next(
        (
            name
            for name in names
            if name and frappe.db.exists(WORKBOOK, name) and frappe.has_permission(WORKBOOK, "read", doc=name)
        ),
        None,
    )
