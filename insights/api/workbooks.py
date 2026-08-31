import frappe
from frappe import _

from insights.decorators import insights_whitelist
from insights.permissions import get_insights_users
from insights.utils import DocShare


def validate_shareable_users(emails):
    """A workbook is shareable with Insights users only.

    The picker cannot always show the person being named - an address typed by
    a user who may not look anyone up still has to land somewhere real.
    """
    if not emails:
        return

    # Administrator owns the workbooks a template import creates and so stays on
    # the share list whenever one of them is re-shared
    shareable = get_insights_users() | {"Administrator"}
    unknown = sorted(set(emails) - shareable)
    if unknown:
        frappe.throw(
            _("Cannot share with {0} - they are not an Insights user").format(", ".join(unknown)),
            title=_("Not an Insights user"),
        )


@insights_whitelist()
def get_workbooks(
    search_term: str | None = None,
    limit: int = 100,
    scope: str | None = None,
):
    """Return workbooks accessible to the current user.

    scope:
        "owned"  -> only workbooks owned by the current user
        "shared" -> only workbooks owned by someone else (still permission filtered)
        None     -> all accessible workbooks
    """
    filters = {}
    if scope == "owned":
        filters["owner"] = frappe.session.user
    elif scope == "shared":
        filters["owner"] = ["!=", frappe.session.user]

    or_filters = {"title": ["like", f"%{search_term}%"]} if search_term else None

    workbooks = frappe.get_list(
        "Insights Workbook",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "title",
            "owner",
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
        views = [view for view in workbook_views if view["reference_name"] == workbook["name"]]
        workbook["views"] = len(views)

    # batch the share lookups into two grouped queries instead of ~2 per
    # workbook (avoids an N+1 over the whole list)
    org_shared, shared_users = _workbook_shares(workbook_names)
    for workbook in workbooks:
        name = workbook["name"]
        if name in org_shared:
            workbook["shared_with_organization"] = True
            continue
        workbook["shared_with"] = [user for user in shared_users.get(name, []) if user != workbook["owner"]]

    return workbooks


def _workbook_shares(names: list[str]) -> tuple[set, dict]:
    """Return (org-shared workbook names, {workbook name -> [users it's read-shared with]}).

    Two queries for the whole list instead of an exists-check + fetch per workbook.
    """
    if not names:
        return set(), {}

    org_shared = set(
        frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Workbook",
                "share_name": ["in", names],
                "everyone": 1,
                "read": 1,
            },
            pluck="share_name",
        )
    )

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
        shared_users.setdefault(row["share_name"], []).append(row["user"])

    return org_shared, shared_users


@insights_whitelist()
def import_workbook(workbook: dict | str):
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
            User.user_image,
        )
        .where(DocShare.share_doctype == "Insights Workbook")
        .where(DocShare.share_name == workbook_name)
        .where(DocShare.everyone == 0)
        .run(as_dict=True)
    )
    owner = frappe.db.get_value("Insights Workbook", workbook_name, "owner")
    owner_info = frappe.db.get_value("User", owner, ["full_name", "user_image"], as_dict=True) or {}
    user_permissions.append(
        {
            "user": owner,
            "full_name": owner_info.get("full_name"),
            "user_image": owner_info.get("user_image"),
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
    workbook_name: str, user_permissions: list, organization_access: str | None = None
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
    validate_shareable_users(allowed_users)
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


ITEM_DOCTYPES = {
    "folder": "Insights Folder",
    "query": "Insights Query v3",
    "chart": "Insights Chart v3",
}


def item_workbook(doctype: str, name) -> str | None:
    """The workbook holding this row, or None if the row is gone.

    The write goes straight to the row, so the permission query that scopes the
    read never sees it - this read is what scopes the write. A dict is not a
    name: `frappe.db` reads one as a filter set and would match every row.

    Gone and held by someone else are different answers, and the callers want
    different things from each, so this reports and they decide.
    """
    if not isinstance(name, str):
        frappe.throw(_("{0} is not the name of a {1}").format(name, doctype))

    return frappe.db.get_value(doctype, name, "workbook")


def refuse_another_workbooks_item(doctype: str, name, holder: str | None, workbook: str) -> None:
    """A row this workbook does not hold is not this caller's to write."""
    if holder != workbook:
        frappe.throw(
            _("{0} {1} does not belong to this workbook").format(doctype, name),
            frappe.PermissionError,
        )


@insights_whitelist()
def move_item_to_folder(item_type: str, item_name: str, folder_name: str | None = None):
    """Move a query/chart to a folder"""
    doctype = ITEM_DOCTYPES.get(item_type)
    if not doctype or doctype == "Insights Folder":
        frappe.throw(_("{0} is not a movable item type").format(item_type))

    item = frappe.get_doc(doctype, item_name)

    if not frappe.has_permission("Insights Workbook", ptype="write", doc=item.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    if folder_name:
        holder = item_workbook("Insights Folder", folder_name)
        if holder is None:
            frappe.throw(_("Insights Folder {0} not found").format(folder_name))
        refuse_another_workbooks_item("Insights Folder", folder_name, holder, item.workbook)

    item.db_set("folder", folder_name, update_modified=False)


@insights_whitelist()
def update_sort_orders(workbook: str, items: list):
    """Order a workbook's own queries, charts and folders"""
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    for item in items:
        doctype = ITEM_DOCTYPES.get(item.get("type"))
        if not doctype:
            frappe.throw(_("{0} is not a workbook item type").format(item.get("type")))

        sort_order = item.get("sort_order")
        if not isinstance(sort_order, int):
            frappe.throw(_("{0} is not a sort order").format(sort_order))

        # the client sends the whole list after a drag, so it can name an item
        # someone else has since deleted. That item has nothing to order.
        holder = item_workbook(doctype, item.get("name"))
        if holder is None:
            continue

        refuse_another_workbooks_item(doctype, item["name"], holder, workbook)

        values = {"sort_order": sort_order}
        if doctype != "Insights Folder":
            folder = item.get("folder")
            if folder:
                # a deleted folder leaves its items at the root, which is what
                # `delete_folder` does. One held by another workbook is refused,
                # because dropping the item at the root would hide the refusal.
                folder_holder = item_workbook("Insights Folder", folder)
                if folder_holder is None:
                    folder = None
                else:
                    refuse_another_workbooks_item("Insights Folder", folder, folder_holder, workbook)
            values["folder"] = folder

        frappe.db.set_value(doctype, item["name"], values, update_modified=False)

    frappe.db.commit()
