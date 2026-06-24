import frappe
from frappe import _

from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_team.insights_team import is_admin
from insights.utils import DocShare


@insights_whitelist()
def get_workbooks(
    search_term: str | None = None,
    limit: int = 100,
    scope: str | None = None,
    folder: str | None = None,
):
    """Return workbooks accessible to the current user.

    scope:
        "owned"  -> only workbooks owned by the current user
        "shared" -> only workbooks owned by someone else (still permission filtered)
        None     -> all accessible workbooks
    folder:
        when provided, only workbooks filed directly under this folder
        (use the sentinel "" / "root" to restrict to unfiled workbooks)
    """
    filters = {}
    if scope == "owned":
        filters["owner"] = frappe.session.user
    elif scope == "shared":
        filters["owner"] = ["!=", frappe.session.user]

    if folder in ("", "root"):
        filters["folder"] = ["is", "not set"]
    elif folder:
        filters["folder"] = folder

    or_filters = {"title": ["like", f"%{search_term}%"]} if search_term else None

    workbooks = frappe.get_list(
        "Insights Workbook",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "title",
            "owner",
            "folder",
            "creation",
            "modified",
        ],
        limit=limit,
    )
    # FIX: figure out how to use frappe.qb while respecting permissions
    # TODO: use frappe.qb to get the view count
    workbook_names = [workbook["name"] for workbook in workbooks]
    workbook_views = frappe.get_all(
        "View Log",
        filters={
            "reference_doctype": "Insights Workbook",
            "reference_name": ["in", workbook_names],
        },
        fields=["reference_name", "name"],
    )
    for workbook in workbooks:
        views = [view for view in workbook_views if str(view["reference_name"]) == str(workbook["name"])]
        workbook["views"] = len(views)

    # batch the share lookups into two grouped queries instead of ~2 per
    # workbook (avoids an N+1 over the whole list)
    org_shared, shared_users = _workbook_shares(workbook_names)
    for workbook in workbooks:
        # share_name is stored as a string; workbook name may be an int — cast to match
        name = str(workbook["name"])
        if name in org_shared:
            workbook["shared_with_organization"] = True
            continue
        workbook["shared_with"] = [user for user in shared_users.get(name, []) if user != workbook["owner"]]

    return workbooks


def _workbook_shares(names: list[str]) -> tuple[set, dict]:
    """Return (org-shared workbook names, {workbook name -> [users it's read-shared with]}).

    Two queries for the whole list instead of an exists-check + fetch per workbook.
    Keys are stringified since DocShare.share_name is stored as a string.
    """
    if not names:
        return set(), {}

    org_shared = {
        str(name)
        for name in frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Workbook",
                "share_name": ["in", names],
                "everyone": 1,
                "read": 1,
            },
            pluck="share_name",
        )
    }

    shared_users: dict[str, list] = {}
    rows = frappe.get_all(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": ["in", names],
            "read": 1,
        },
        fields=["share_name", "user"],
    )
    for row in rows:
        shared_users.setdefault(str(row["share_name"]), []).append(row["user"])

    return org_shared, shared_users


@insights_whitelist()
def import_workbook(workbook: dict):
    from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook

    return import_workbook(workbook)


@insights_whitelist()
def get_share_permissions(workbook_name: str):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"), frappe.PermissionError)

    DocShare = frappe.qb.DocType("DocShare")
    User = frappe.qb.DocType("User")

    user_permissions = (
        frappe.qb.from_(DocShare)
        .left_join(User)
        .on(DocShare.user == User.name)
        .select(
            DocShare.user,
            DocShare.read,
            DocShare.write,
            DocShare.share,
            User.full_name,
        )
        .where(DocShare.share_doctype == "Insights Workbook")
        .where(DocShare.share_name == workbook_name)
        .where(DocShare.everyone == 0)
        .run(as_dict=True)
    )
    owner = frappe.db.get_value("Insights Workbook", workbook_name, "owner")
    user_permissions.append(
        {
            "user": owner,
            "full_name": frappe.get_value("User", owner, "full_name"),
            "read": 1,
            "write": 1,
        }
    )

    public_docshare = frappe.db.get_value(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": workbook_name,
            "everyone": 1,
        },
        fieldname=["read", "write"],
        as_dict=True,
    )
    organization_access = None
    if public_docshare:
        organization_access = "edit" if public_docshare["write"] else "view"

    return {
        "user_permissions": user_permissions,
        "organization_access": organization_access,
    }


@insights_whitelist()
def update_share_permissions(
    workbook_name: str, user_permissions: dict, organization_access: str | None = None
):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"), frappe.PermissionError)

    existing_shares = frappe.get_all(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": workbook_name,
        },
        fields=["name", "user", "everyone"],
    )

    allowed_users = {permission["user"] for permission in user_permissions}
    for share in existing_shares:
        if share.user and share.user not in allowed_users:
            frappe.delete_doc("DocShare", share.name, ignore_permissions=True)

    for permission in user_permissions:
        doc = DocShare.get_or_create_doc(
            share_doctype="Insights Workbook",
            share_name=workbook_name,
            user=permission["user"],
        )
        doc.read = permission["read"]
        doc.write = permission["write"]
        doc.notify_by_email = 0
        doc.save(ignore_permissions=True)

    public_docshare = DocShare.get_or_create_doc(
        share_doctype="Insights Workbook",
        share_name=workbook_name,
        everyone=1,
    )
    if organization_access:
        public_docshare.read = 1
        public_docshare.write = organization_access == "edit"
        public_docshare.notify_by_email = 0
        public_docshare.save(ignore_permissions=True)
    elif public_docshare.name:
        public_docshare.delete(ignore_permissions=True)


# folder Management APIs


@insights_whitelist()
def create_folder(workbook: str, title: str, folder_type: str):
    """Create a new folder in workbook"""
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    current_folders = frappe.db.count("Insights Folder", filters={"workbook": workbook, "type": folder_type})

    folder = frappe.new_doc("Insights Folder")
    folder.workbook = workbook
    folder.title = title
    folder.type = folder_type
    folder.sort_order = current_folders
    folder.insert()

    return folder.name


@insights_whitelist()
def rename_folder(folder_name: str, new_title: str):
    """Rename a folder"""
    folder = frappe.get_doc("Insights Folder", folder_name)
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=folder.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    folder.title = new_title
    folder.save()

    return folder.name


@insights_whitelist()
def delete_folder(folder_name: str, move_items_to_root: bool = True):
    """Delete folder and move items to root"""
    folder = frappe.get_doc("Insights Folder", folder_name)
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=folder.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    if move_items_to_root:
        # move all queries to root
        frappe.db.set_value(
            "Insights Query v3",
            {"folder": folder_name},
            "folder",
            None,
            update_modified=False,
        )
        # move all charts to root
        frappe.db.set_value(
            "Insights Chart v3",
            {"folder": folder_name},
            "folder",
            None,
            update_modified=False,
        )

    frappe.delete_doc("Insights Folder", folder_name)


@insights_whitelist()
def toggle_folder_expanded(folder_name: str, is_expanded: bool):
    """Toggle folder expanded state"""
    folder = frappe.get_doc("Insights Folder", folder_name)
    if not frappe.has_permission("Insights Workbook", ptype="read", doc=folder.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    folder.db_set("is_expanded", is_expanded, update_modified=False)


@insights_whitelist()
def move_item_to_folder(item_type: str, item_name: str, folder_name: str | None = None):
    """Move a query/chart to a folder"""
    doctype = "Insights Query v3" if item_type == "query" else "Insights Chart v3"
    item = frappe.get_doc(doctype, item_name)

    if not frappe.has_permission("Insights Workbook", ptype="write", doc=item.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    if folder_name:
        folder = frappe.get_doc("Insights Folder", folder_name)
        if folder.workbook != item.workbook:
            frappe.throw(_("Folder and item must belong to the same workbook"))

    item.db_set("folder", folder_name, update_modified=False)


@insights_whitelist()
def update_sort_orders(workbook: str, items: list):
    """Bulk update sort orders"""
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    for item in items:
        if item["type"] == "folder":
            frappe.db.set_value(
                "Insights Folder",
                item["name"],
                {
                    "sort_order": item["sort_order"],
                },
                update_modified=False,
            )
        elif item["type"] == "query":
            frappe.db.set_value(
                "Insights Query v3",
                item["name"],
                {
                    "sort_order": item["sort_order"],
                    "folder": item.get("folder"),
                },
                update_modified=False,
            )
        elif item["type"] == "chart":
            frappe.db.set_value(
                "Insights Chart v3",
                item["name"],
                {
                    "sort_order": item["sort_order"],
                    "folder": item.get("folder"),
                },
                update_modified=False,
            )

    frappe.db.commit()


# Workbook Folder (org-level) APIs
#
# These organize workbooks themselves into a shared, org-level tree.
# This is distinct from `Insights Folder` above, which organizes
# queries/charts *inside* a single workbook.


def _ensure_workbook_folder_admin():
    if not is_admin(frappe.session.user):
        frappe.throw(
            _("Only an Insights Admin can manage workbook folders"),
            frappe.PermissionError,
        )


@insights_whitelist()
def get_workbook_folders():
    """Return the full org-level workbook folder tree.

    The client builds the subfolder list and breadcrumb from this flat tree and
    fetches the workbooks of a given folder via `get_workbooks(folder=...)`.
    """
    folders = frappe.get_all(
        "Insights Workbook Folder",
        fields=["name", "title", "parent_folder"],
        order_by="title asc",
    )
    # name is an autoincrement int; link fields store it as a string, so expose
    # it as a string everywhere to keep comparisons consistent
    for f in folders:
        f["name"] = str(f["name"])
    return folders


@insights_whitelist()
def create_workbook_folder(title: str, parent_folder: str | None = None):
    """Create an org-level workbook folder (admin only)."""
    _ensure_workbook_folder_admin()

    folder = frappe.new_doc("Insights Workbook Folder")
    folder.title = title
    folder.parent_folder = parent_folder or None
    folder.insert()
    return str(folder.name)


@insights_whitelist()
def rename_workbook_folder(folder_name: str, new_title: str):
    """Rename an org-level workbook folder (admin only)."""
    _ensure_workbook_folder_admin()

    folder = frappe.get_doc("Insights Workbook Folder", folder_name)
    folder.title = new_title
    folder.save()
    return folder.name


@insights_whitelist()
def delete_workbook_folder(folder_name: str):
    """Delete an empty org-level workbook folder (admin only).

    Deletion is blocked while the folder still contains subfolders or workbooks.
    """
    _ensure_workbook_folder_admin()

    has_subfolders = frappe.db.exists("Insights Workbook Folder", {"parent_folder": folder_name})
    has_workbooks = frappe.db.exists("Insights Workbook", {"folder": folder_name})
    if has_subfolders or has_workbooks:
        frappe.throw(
            _("Cannot delete a folder that is not empty. Move its contents out first."),
        )

    frappe.delete_doc("Insights Workbook Folder", folder_name)


@insights_whitelist()
def move_workbook_to_folder(workbook: str, folder: str | None = None):
    """File a workbook into a folder (or back to root when folder is None).

    A user can file workbooks they can write to; the org folder structure
    itself is admin-governed, but filing is open.
    """
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    if folder and not frappe.db.exists("Insights Workbook Folder", folder):
        frappe.throw(_("Folder {0} does not exist").format(folder))

    frappe.db.set_value("Insights Workbook", workbook, "folder", folder or None)


@insights_whitelist()
def move_workbooks_to_folder(workbooks: list, folder: str | None = None):
    """Bulk-file workbooks into a folder (or back to root when folder is None).

    Workbooks the user can't write to are skipped; the count actually moved is
    returned so the client can report it.
    """
    if folder and not frappe.db.exists("Insights Workbook Folder", folder):
        frappe.throw(_("Folder {0} does not exist").format(folder))

    moved = 0
    for workbook in workbooks:
        if not frappe.has_permission("Insights Workbook", ptype="write", doc=workbook):
            continue
        frappe.db.set_value("Insights Workbook", workbook, "folder", folder or None)
        moved += 1

    return moved
