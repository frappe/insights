import frappe

from insights.permissions import VISIBILITY_DOCTYPES, WORKBOOK_MEMBERS


def execute():
    """A share on a workbook member is a named read share on a dashboard or chart
    (`is_member_share`), and frappe reads a share after the controller refuses.
    A named one on a dashboard or chart keeps its read; every other one goes."""
    DocShare = frappe.qb.DocType("DocShare")
    on_a_member = DocShare.share_doctype.isin(WORKBOOK_MEMBERS)
    named_read = (
        DocShare.share_doctype.isin(VISIBILITY_DOCTYPES)
        & DocShare.user.isnotnull()
        & (DocShare.user != "")
        & (DocShare.everyone == 0)
        & (DocShare.read == 1)
    )

    frappe.qb.from_(DocShare).delete().where(on_a_member & ~named_read).run()
    (
        frappe.qb.update(DocShare)
        .set(DocShare.write, 0)
        .set(DocShare.share, 0)
        .set(DocShare.submit, 0)
        .where(on_a_member)
        .run()
    )
