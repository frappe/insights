import frappe

from insights.permissions import EVERYONE, VISIBILITY_DOCTYPES, visibility_level


def execute():
    """
    `visibility` absorbs the org-wide DocShare as its `Everyone` level, so
    content an org-wide share admitted every signed-in user to moves to
    `visibility = "Everyone"` and the share row goes.

    Only the dashboard share dialog ever wrote such a row, and it wrote read
    alone. A row carrying write or share is left where it is: no level grants
    either, so dropping it would take something away.

    A chart carries the same levels and the permission query reads an org-wide
    row for neither doctype any more, so both are named here.
    """
    for doctype in VISIBILITY_DOCTYPES:
        shares = frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": doctype,
                "everyone": 1,
                "read": 1,
                "write": 0,
                "share": 0,
            },
            fields=["name", "share_name"],
        )
        if not shares:
            continue

        for name in {share.share_name for share in shares}:
            visibility = frappe.db.get_value(doctype, name, "visibility")
            if visibility_level(visibility) < visibility_level(EVERYONE):
                frappe.db.set_value(doctype, name, "visibility", EVERYONE, update_modified=False)

        for share in shares:
            frappe.delete_doc("DocShare", share.name, ignore_permissions=True, force=True)
