import frappe
from ibis import _

from insights.decorators import insights_whitelist
from insights.utils import DocShare


@insights_whitelist()
def get_workbooks(search_term=None, limit=100):
    workbooks = frappe.get_list(
        "Insights Workbook",
        or_filters={
            "owner": ["like", f"%{search_term}%" if search_term else "%"],
            "title": ["like", f"%{search_term}%" if search_term else "%"],
        },
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
        views = [view for view in workbook_views if str(view["reference_name"]) == str(workbook["name"])]
        workbook["views"] = len(views)

    for workbook in workbooks:
        organization_has_access = frappe.db.exists(
            "DocShare",
            {
                "share_doctype": "Insights Workbook",
                "share_name": workbook["name"],
                "everyone": 1,
                "read": 1,
            },
        )
        if organization_has_access:
            workbook["shared_with_organization"] = True
            continue

        shared_with = frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Workbook",
                "share_name": workbook["name"],
                "user": ["!=", workbook["owner"]],
                "read": 1,
            },
            pluck="user",
        )
        workbook["shared_with"] = shared_with

    return workbooks


@insights_whitelist()
def import_workbook(workbook):
    from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook

    return import_workbook(workbook)


@insights_whitelist()
def get_share_permissions(workbook_name):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"))

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
def update_share_permissions(workbook_name, user_permissions, organization_access: str | None = None):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"))

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
def create_folder(workbook, title, folder_type):
    """Create a new folder in workbook"""
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=workbook):
        frappe.throw(_("You do not have permission to modify this workbook"))

    max_sort_order = frappe.db.get_all(
        "Insights Folder",
        filters={"workbook": workbook, "type": folder_type},
        fields=["max(sort_order) as max_sort_order"],as_list=True,
      )
    max_sort_order = max_sort_order[0][0] if max_sort_order and max_sort_order[0][0] is not None else -1

    folder = frappe.new_doc("Insights Folder")
    folder.workbook = workbook
    folder.title = title
    folder.type = folder_type
    folder.sort_order = max_sort_order + 1
    folder.insert()

    return folder.name

@insights_whitelist()
def rename_folder(folder_name, new_title):
    """Rename a folder"""
    folder = frappe.get_doc("Insights Folder", folder_name)
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=folder.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"))

    folder.title = new_title
    folder.save()

    return folder.name

@insights_whitelist()
def delete_folder(folder_name, move_items_to_root=True):
    """Delete folder and move items to root"""
    folder = frappe.get_doc("Insights Folder", folder_name)
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=folder.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"))

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
def toggle_folder_expanded(folder_name, is_expanded):
    """Toggle folder expanded state"""
    folder = frappe.get_doc("Insights Folder", folder_name)
    if not frappe.has_permission("Insights Workbook", ptype="read", doc=folder.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"))

    folder.db_set("is_expanded", is_expanded, update_modified=False)

@insights_whitelist()
def move_item_to_folder(item_type, item_name, folder_name=None):
    """Move a query/chart to a folder"""
    doctype = "Insights Query v3" if item_type == "query" else "Insights Chart v3"
    item = frappe.get_doc(doctype, item_name)

    if not frappe.has_permission("Insights Workbook", ptype="write", doc=item.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"))

    if folder_name:
        folder = frappe.get_doc("Insights Folder", folder_name)
        if folder.workbook != item.workbook:
            frappe.throw(_("Folder and item must belong to the same workbook"))

    item.db_set("folder", folder_name, update_modified=False)


@insights_whitelist()
def update_sort_orders(workbook, items):
    """Bulk update sort orders"""
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=workbook):
        frappe.throw(_("You do not have permission to modify this workbook"))

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
