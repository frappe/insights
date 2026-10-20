import frappe

from insights.patches.share_workbooks_with_member_owners import WORKBOOK, share_workbook, workbook_title
from insights.permissions import VISIBILITY_DOCTYPES, WORKBOOK_MEMBERS, get_insights_users, workbook_of
from insights.upgrade import add_item

MEMBER_LABELS = {
    "Insights Query v3": "query",
    "Insights Chart v3": "chart",
    "Insights Dashboard v3": "dashboard",
    "Insights Alert": "alert",
    "Insights Folder": "folder",
}


def execute():
    """A share on a workbook member is a named read share on a dashboard or chart
    (`is_member_share`), and frappe reads a share after the controller refuses.
    A named one on a dashboard or chart keeps its read; every other one goes.

    A user a removed share named gets the same access on the workbook, which is
    now the only way to it. A share with everyone is not widened to the whole
    workbook: an earlier patch already turned a read one on a dashboard or chart
    into the `Everyone` level, and an admin is told about the rest.
    """
    DocShare = frappe.qb.DocType("DocShare")
    on_a_member = DocShare.share_doctype.isin(WORKBOOK_MEMBERS)
    named_read = (
        DocShare.share_doctype.isin(VISIBILITY_DOCTYPES)
        & DocShare.user.isnotnull()
        & (DocShare.user != "")
        & (DocShare.everyone == 0)
        & (DocShare.read == 1)
    )
    flags_beyond_read = (DocShare.write == 1) | (DocShare.share == 1) | (DocShare.submit == 1)

    changed = (
        frappe.qb.from_(DocShare)
        .select(
            DocShare.share_doctype,
            DocShare.share_name,
            DocShare.user,
            DocShare.everyone,
            DocShare.write,
            DocShare.share,
        )
        .where(on_a_member & (~named_read | flags_beyond_read))
        .run(as_dict=True)
    )
    move_to_workbooks(changed)

    frappe.qb.from_(DocShare).delete().where(on_a_member & ~named_read).run()
    (
        frappe.qb.update(DocShare)
        .set(DocShare.write, 0)
        .set(DocShare.share, 0)
        .set(DocShare.submit, 0)
        .where(on_a_member)
        .run()
    )


def move_to_workbooks(shares: list) -> None:
    users = get_insights_users()
    granted, kinds, everyone = {}, {}, {}
    for share in shares:
        if not frappe.db.exists(share.share_doctype, share.share_name):
            continue
        workbook = workbook_of(frappe.get_doc(share.share_doctype, share.share_name))
        if not workbook or not frappe.db.exists(WORKBOOK, workbook):
            continue
        if share.everyone:
            if share.write or share.share or share.share_doctype not in VISIBILITY_DOCTYPES:
                everyone.setdefault(workbook, []).append(share)
            continue
        ptype = "share" if share.share else "write" if share.write else "read"
        if share.user not in users or frappe.has_permission(WORKBOOK, ptype, doc=workbook, user=share.user):
            continue
        share_workbook(workbook, share.user, write=share.write, share=share.share)
        granted.setdefault(workbook, set()).add(share.user)
        kinds.setdefault(workbook, set()).add(share.share_doctype)

    for workbook in sorted({*granted, *everyone}):
        add_item(
            "P7",
            message(workbook, granted.get(workbook), kinds.get(workbook), everyone.get(workbook)),
            reference=(WORKBOOK, workbook),
        )


def message(workbook: str, users: set | None, doctypes: set | None, everyone: list | None) -> str:
    title = workbook_title(workbook)
    parts = []
    if users:
        shared = " and ".join(sorted(f"{MEMBER_LABELS.get(doctype, doctype)}s" for doctype in doctypes or ()))
        parts.append(f"now shared with {', '.join(sorted(users))}, as its {shared} were")
    for share in everyone or []:
        label = MEMBER_LABELS.get(share.share_doctype, share.share_doctype)
        member_title = frappe.db.get_value(share.share_doctype, share.share_name, "title") or share.share_name
        to_edit = " to edit" if share.write else ""
        parts.append(f'removed the share of {label} "{member_title}" with everyone{to_edit}')
    return f'"{title}": {"; ".join(parts)}'
