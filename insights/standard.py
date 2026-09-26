# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
"""A workbook an app ships as a file.

Insights imports the file after a migrate or an install, through frappe's
`import_file_by_path`. The workbook refuses a write outside developer mode,
writes its file back when a developer saves it, and removes the file when it
goes. A member calls these for its workbook, so the workbook decides for all its
members.
"""

import os
from contextlib import contextmanager

import frappe
from frappe.modules.export_file import delete_folder as delete_document_folder
from frappe.modules.import_file import import_file_by_path, read_doc_from_file
from frappe.modules.utils import export_module_json, get_module_app

# The write paths frappe runs itself.
SYSTEM_WRITE_FLAGS = ("in_import", "in_fixtures", "in_migrate", "in_install", "in_patch")

WORKBOOK = "Insights Workbook"

# A deleted workbook deletes its members too. A member's own export would then
# write the file back after the workbook removed it.
BEING_DELETED = "insights_workbooks_being_deleted"


@contextmanager
def deleting(workbook: str):
    being_deleted = frappe.flags.setdefault(BEING_DELETED, set())
    being_deleted.add(workbook)
    try:
        yield
    finally:
        being_deleted.discard(workbook)


def validate_standard(doc) -> None:
    """Refuse a write to a standard document outside developer mode.

    `running` reads `is_standard` to let a chart past the site's team grants
    and Table Restrictions. A site user can write the field, because
    `frappe.client.set_value` does not enforce `read_only`. Without this check,
    an author could mark their own workbook standard and read every table the
    site denies them.
    """
    if frappe.conf.developer_mode or any(frappe.flags.get(flag) for flag in SYSTEM_WRITE_FLAGS):
        return

    was_standard = not doc.is_new() and frappe.db.get_value(doc.doctype, doc.name, "is_standard")
    if not (was_standard or doc.get("is_standard")):
        return

    frappe.throw(
        frappe._("{0} belongs to its app and can only be changed in developer mode.").format(
            frappe.bold(doc.get("title") or doc.name)
        ),
        title=frappe._("Not Editable"),
    )


def validate_overwrite(docdict: dict) -> None:
    """Refuse a file that would replace a workbook its app does not own.

    frappe deletes the row a file names before it inserts the file, and
    `is_standard` lets a chart past the site's team grants. So a shipped file
    must never replace a workbook the site made, or one that another app ships.
    """
    row = frappe.db.get_value(WORKBOOK, docdict["name"], ["is_standard", "module"], as_dict=True)
    if not row:
        return

    app = get_module_app(docdict["module"])
    if not row.is_standard:
        frappe.throw(
            frappe._("{0} ships {1} {2}, but this site already has a document of that name.").format(
                app, WORKBOOK, frappe.bold(docdict["name"])
            )
        )

    owner = get_module_app(row.module)
    if owner != app:
        frappe.throw(
            frappe._("{0} ships {1} {2}, which belongs to {3}.").format(
                app, WORKBOOK, frappe.bold(docdict["name"]), owner
            )
        )


def export(doc) -> None:
    """Write the workbook's file, in developer mode."""
    if not frappe.conf.developer_mode or frappe.flags.in_import:
        return

    before = doc.get_doc_before_save()
    if before and before.is_standard and (not doc.is_standard or before.module != doc.module):
        delete_folder(before)

    if not doc.is_standard:
        return

    # Another site imports the file only when its `modified` is newer than the
    # row there, and a member's edit leaves the workbook's own `modified` as it was.
    doc.db_set("modified", frappe.utils.now(), update_modified=False)
    export_module_json(doc, True, doc.module)


def delete_folder(doc, name: str | None = None) -> None:
    """`name` is the old name after a rename."""
    if not frappe.conf.developer_mode or not doc.get("module"):
        return

    delete_document_folder(doc.module, doc.doctype, name or doc.name)


def import_shipped(apps: list[str] | None = None) -> None:
    """Import the workbook files that `apps` ship, or every installed app's by default.

    This does not use frappe's `importable_doctypes` walk. That walk runs in
    each app's own sync, in install order. So an app installed before Insights
    would have its files imported before this doctype's schema is synced, and
    never imported when Insights is installed after it. After a migrate or an
    install, every schema is in place.
    """
    for app, module in app_modules():
        if apps and app not in apps:
            continue

        folder = os.path.join(frappe.get_module_path(module), frappe.scrub(WORKBOOK))
        if not os.path.isdir(folder):
            continue

        for stem in sorted(os.listdir(folder)):
            path = os.path.join(folder, stem, f"{stem}.json")
            if os.path.exists(path):
                import_file_by_path(path, ignore_version=True)


def delete_unshipped() -> None:
    """Delete the standard workbooks whose file no installed app ships any more.

    frappe's own `remove_orphan_entities` has no filter for this doctype.
    Without one, every workbook a site made would look like an orphan.
    """
    for row in frappe.get_all(WORKBOOK, filters={"is_standard": 1}, fields=["name", "module"]):
        # `get_module_path` throws for a module whose app is gone
        if not ships_module(row.module) or not os.path.exists(file_path(WORKBOOK, row.name, row.module)):
            frappe.delete_doc(WORKBOOK, row.name, force=True, ignore_permissions=True)


def guard_member(doc) -> None:
    """Refuse a write to a member of a standard workbook.

    Checks both the workbook it belongs to and the one it is moving to, so a
    site cannot add a member to a workbook its app owns.
    """
    for workbook in workbooks_of(doc):
        validate_standard(frappe.get_doc(WORKBOOK, workbook))


def export_member(doc) -> None:
    """Write the file of the workbook the member belongs to."""
    for workbook in workbooks_of(doc):
        export(frappe.get_doc(WORKBOOK, workbook))


def workbooks_of(doc) -> list[str]:
    """The workbooks a write to `doc` affects: the one it is in, and the one it
    is moving to. Only the standard ones, because the others need no check."""
    names = []
    if not doc.is_new():
        names.append(frappe.db.get_value(doc.doctype, doc.name, "workbook"))
    names.append(doc.workbook)

    being_deleted = frappe.flags.get(BEING_DELETED) or set()
    return [
        name
        for name in dict.fromkeys(names)
        if name and name not in being_deleted and frappe.db.get_value(WORKBOOK, name, "is_standard")
    ]


def file_path(doctype: str, name: str, module: str) -> str:
    """The file `module` would ship `name` as."""
    stem = frappe.scrub(name)
    return os.path.join(frappe.get_module_path(module), frappe.scrub(doctype), stem, f"{stem}.json")


def app_modules() -> list[tuple[str, str]]:
    """Every module an installed app ships, as `(app, module)`.

    Shipped files are read back from these modules. `import_shipped` walks the
    installed apps and their `modules.txt`, and `delete_unshipped` deletes
    every standard workbook without a file there. A `Module Def` that a site
    made for itself is not in this list. So a file written into it is an orphan
    that the next `bench migrate` deletes. That deletes the workbook and,
    through `on_trash`, every query, chart, dashboard and folder in it.
    """
    return [
        (app, module) for app in frappe.get_installed_apps() for module in sorted(frappe.get_module_list(app))
    ]


def ships_module(module: str | None) -> bool:
    """Whether an installed app ships `module`."""
    return any(module == name for _, name in app_modules())


def export_modules() -> list[dict]:
    """The modules an author may export a workbook into, and the folder each
    one writes to.

    It is `app_modules` minus the modules this bench cannot write. A file is a
    change to the app's source. So a module the bench can only read cannot take
    an export, and neither can a site outside developer mode.

    Presentation only. `InsightsWorkbook.validate` refuses a module that no app
    ships, so a save that skips this dialog is refused too.
    """
    if not frappe.conf.developer_mode:
        return []

    modules = []
    for app, module in app_modules():
        root = os.path.join(frappe.get_module_path(module), frappe.scrub(WORKBOOK))

        writable = os.path.dirname(root) if not os.path.isdir(root) else root
        if not os.access(writable, os.W_OK):
            continue

        # the full path, as `check_file_is_free` shows it in its error
        modules.append({"module": module, "app": app, "folder": root})

    return modules


def check_file_is_free(doctype: str, name: str, module: str) -> None:
    """Refuse a name whose file another document in `module` already has.

    The file is named after `scrub(name)`, and two names can scrub to one
    folder. The second document would then overwrite the first one's file.
    """
    path = file_path(doctype, name, module)
    if not os.path.exists(os.path.dirname(path)):
        return

    if os.path.exists(path) and read_doc_from_file(path).get("name") == name:
        return

    frappe.throw(
        frappe._("{0} already holds a file at {1}.").format(module, frappe.bold(path)),
        title=frappe._("Name Taken"),
    )


def is_standard_member(doc) -> bool:
    """Whether `doc` belongs to a workbook its app ships.

    Read from the workbook's row, never from the member in hand. A member's own
    `is_standard` copies the workbook's flag, and a site user can write it,
    because `frappe.client.set_value` does not enforce `read_only`. This answer
    decides whether an execution reads its tables past the site's team grants.
    The file on disk decides what is standard content, and the workbook row is
    what frappe imported from that file.
    """
    stored = doc.name and frappe.db.get_value(doc.doctype, doc.name, "workbook")
    workbook = stored or doc.get("workbook")
    return bool(workbook and frappe.db.get_value(WORKBOOK, workbook, "is_standard"))


def is_read_only(workbook: str | None) -> bool:
    """Whether the site may change `workbook` and what is in it.

    The part of `insights.permissions.can_write` that depends on the site, not
    the caller.
    """
    if not workbook or frappe.conf.developer_mode:
        return False

    return bool(frappe.db.get_value(WORKBOOK, workbook, "is_standard"))
