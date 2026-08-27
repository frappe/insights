# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
"""An invitation grants access to Insights. It does not sign anyone in.

Two rules, held together because either alone is incomplete: the key is stored
as a hash, so the stored value is not the credential, and acceptance signs in
only the account it just created.
"""

from unittest.mock import patch
from urllib.parse import quote

import frappe
from frappe.tests import IntegrationTestCase

from insights.api.user import accept_invitation
from insights.utils import get_app_url


def make_invitation(email):
    """Insert an invitation without needing an outgoing email account."""
    invitation = frappe.new_doc("Insights User Invitation")
    invitation.email = email
    with patch.object(frappe, "sendmail"):
        invitation.insert(ignore_permissions=True)
    return invitation


class TestInvitationKeyIsStoredHashed(IntegrationTestCase):
    def test_the_key_is_stored_hashed(self):
        from insights.insights.doctype.insights_user_invitation.insights_user_invitation import hash_key

        invitation = make_invitation("hashed-key@example.com")
        stored = frappe.db.get_value("Insights User Invitation", invitation.name, "key")
        self.assertNotEqual(stored, invitation._plain_key)
        self.assertEqual(stored, hash_key(invitation._plain_key))

    def test_the_invitation_email_carries_the_key(self):
        """The mailed link has to hold the key itself, or nothing can redeem it."""
        with patch.object(frappe, "sendmail") as sendmail:
            invitation = frappe.new_doc("Insights User Invitation")
            invitation.email = "mailed-key@example.com"
            invitation.insert(ignore_permissions=True)

        link = sendmail.call_args.kwargs["args"]["invite_link"]
        self.assertIn(invitation._plain_key, link)
        self.assertNotIn(invitation.key, link)

    def test_the_stored_value_is_not_the_key(self):
        """What the row holds cannot be redeemed; what was mailed can."""
        from insights.insights.doctype.insights_user_invitation.insights_user_invitation import (
            get_invitation_by_key,
        )

        invitation = make_invitation("inert-key@example.com")
        stored = frappe.db.get_value("Insights User Invitation", invitation.name, "key")
        self.assertIsNone(get_invitation_by_key(stored))
        self.assertEqual(get_invitation_by_key(invitation._plain_key), invitation.name)

    def test_only_admins_hold_a_grant_on_the_doctype(self):
        """The users screen reads invitations through an admin-only endpoint, so
        no other role needs this doctype."""
        roles = frappe.get_all(
            "DocPerm",
            filters={"parent": "Insights User Invitation", "role": "Insights User"},
            pluck="name",
        )
        self.assertEqual(roles, [])


class TestInvitationDoesNotAuthenticate(IntegrationTestCase):
    def setUp(self):
        # there is no login manager outside a request, so record the call instead
        self.logged_in_as = []
        frappe.local.login_manager = frappe._dict(login_as=self.logged_in_as.append)
        self.addCleanup(self.drop_login_manager)

    def drop_login_manager(self):
        frappe.local.login_manager = None

    def redeem(self, invitation):
        # older rows stored the key itself
        key = getattr(invitation, "_plain_key", invitation.key)
        frappe.local.response = frappe._dict()
        accept_invitation(key=key)
        return frappe.local.response

    def test_an_existing_account_is_not_signed_in(self):
        """The invitation still applies; the sign-in is left to the account holder."""
        email = "existing-account@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc(doctype="User", email=email, first_name="Existing", send_welcome_email=0).insert(
                ignore_permissions=True
            )

        invitation = make_invitation(email)
        response = self.redeem(invitation)

        self.assertEqual(self.logged_in_as, [])
        # the link still ends in Insights: the login page carries them there
        self.assertEqual(response.location, f"/login?redirect-to={quote(get_app_url())}")
        # the invitation still did its job
        self.assertEqual(
            frappe.db.get_value("Insights User Invitation", invitation.name, "status"), "Accepted"
        )
        self.assertIn("Insights User", frappe.get_roles(email))

    def test_a_new_invitee_is_signed_in(self):
        """A new invitee has no password yet, so the link is how they first get in."""
        email = "brand-new-invitee@example.com"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)

        invitation = make_invitation(email)
        response = self.redeem(invitation)

        self.assertEqual(self.logged_in_as, [email])
        self.assertNotEqual(response.location, "/login")
        self.assertIn("Insights User", frappe.get_roles(email))

    def test_an_unknown_key_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            accept_invitation(key="not-a-real-key")
