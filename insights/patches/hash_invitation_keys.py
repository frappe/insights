import frappe

from insights.insights.doctype.insights_user_invitation.insights_user_invitation import hash_key


def execute():
    """Replace every stored invitation key with its hash.

    Hashing in place keeps the links already mailed working: an incoming key
    hashes to what is now stored.
    """
    invitations = frappe.get_all(
        "Insights User Invitation",
        filters={"key": ["is", "set"]},
        fields=["name", "key"],
    )
    for invitation in invitations:
        # a re-run must not hash a hash
        if len(invitation.key) == 64:
            continue
        frappe.db.set_value(
            "Insights User Invitation",
            invitation.name,
            "key",
            hash_key(invitation.key),
            update_modified=False,
        )
