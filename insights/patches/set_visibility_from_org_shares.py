import frappe

from insights.permissions import EVERYONE, VISIBILITY_DOCTYPES, visibility_level


def execute():
    """
    `visibility` absorbs the org-wide DocShare as its `Everyone` level, so
    content an org-wide share let every signed-in user read moves to
    `visibility = "Everyone"` and the share row goes.

    Every org-wide row goes, whatever flags it has. The permission query
    reads none of them for these two doctypes any more, so a row left behind
    would grant nothing at all - read included - while looking like a grant.
    Write and share have no level to move to: no level grants either, and the
    workbook is where a collaborator is named.
    """
    for doctype in VISIBILITY_DOCTYPES:
        shares = frappe.get_all(
            "DocShare",
            filters={"share_doctype": doctype, "everyone": 1},
            fields=["share_name", "read"],
        )
        if not shares:
            continue

        for name in {share.share_name for share in shares if share.read}:
            visibility = frappe.db.get_value(doctype, name, "visibility")
            if visibility_level(visibility) < visibility_level(EVERYONE):
                frappe.db.set_value(doctype, name, "visibility", EVERYONE, update_modified=False)

        frappe.db.delete("DocShare", {"share_doctype": doctype, "everyone": 1})
