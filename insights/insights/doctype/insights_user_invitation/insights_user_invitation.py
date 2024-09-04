# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import (
    add_days,
    get_datetime,
    now,
    split_emails,
    validate_email_address,
)

from insights.decorators import validate_type

EXPIRY_DAYS = 1


class InsightsUserInvitation(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        accepted_at: DF.Datetime | None
        email: DF.Data
        email_sent_at: DF.Datetime | None
        invited_by: DF.Link | None
        key: DF.Data | None
        name: DF.Int | None
        status: DF.Literal["Pending", "Accepted", "Expired"]
    # end: auto-generated types

    def has_expired(self):
        return self.status == "Pending" and get_datetime(self.creation) < get_datetime(
            add_days(now(), -EXPIRY_DAYS)
        )

    def before_insert(self):
        validate_email_address(self.email, True)
        self.key = frappe.generate_hash(length=12)
        self.invited_by = frappe.session.user
        self.status = "Pending"

    def after_insert(self):
        self.invite_via_email()

    def invite_via_email(self):
        invite_link = frappe.utils.get_url(
            f"/api/method/insights.insights.doctype.insights_user_invitation.insights_user_invitation.accept_invitation?key={self.key}"
        )
        if frappe.local.dev_server:
            print(f"Invite link for {self.email}: {invite_link}")

        title = "Insights"
        template = "insights_invitation"

        frappe.sendmail(
            recipients=self.email,
            subject=f"{title} Invitation",
            template=template,
            args={"title": title, "invite_link": invite_link},
            now=True,
        )
        self.db_set("email_sent_at", frappe.utils.now())

    @frappe.whitelist()
    def accept_invitation(self):
        frappe.only_for("System Manager")
        self.accept()

    def accept(self):
        if self.has_expired():
            self.db_set("status", "Expired", commit=True)
            frappe.throw("Invalid or expired key")

        if self.status == "Expired":
            frappe.throw("Invalid or expired key")

        if self.status == "Accepted":
            frappe.throw("Invitation already accepted")

        user = self.create_user_if_not_exists()
        user.append_roles("Insights User")
        user.save(ignore_permissions=True)

        self.status = "Accepted"
        self.accepted_at = frappe.utils.now()
        self.save(ignore_permissions=True)

    def create_user_if_not_exists(self):
        if not frappe.db.exists("User", self.email):
            first_name = self.email.split("@")[0].title()
            user = frappe.get_doc(
                doctype="User",
                user_type="Website User",
                email=self.email,
                send_welcome_email=0,
                first_name=first_name,
            ).insert(ignore_permissions=True)
        else:
            user = frappe.get_doc("User", self.email)
        return user


@frappe.whitelist(allow_guest=True)
@validate_type
def accept_invitation(key: str):
    if not key:
        frappe.throw("Invalid or expired key")

    invitation_name = frappe.db.exists("Insights User Invitation", {"key": key})
    if not invitation_name:
        frappe.throw("Invalid or expired key")

    invitation = frappe.get_doc("Insights User Invitation", invitation_name)
    invitation.accept()
    invitation.reload()

    if invitation.status == "Accepted":
        frappe.local.login_manager.login_as(invitation.email)
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/insights"


@frappe.whitelist()
@validate_type
def invite_users(emails: str):
    if not emails:
        return

    email_string = validate_email_address(emails, throw=False)
    email_list = split_emails(email_string)
    if not email_list:
        return

    existing_invites = frappe.db.get_all(
        "Insights User Invitation",
        filters={
            "email": ["in", email_list],
            "status": ["in", ["Pending", "Accepted"]],
        },
        pluck="email",
    )

    new_invites = list(set(email_list) - set(existing_invites))
    for email in new_invites:
        invite = frappe.new_doc("Insights User Invitation")
        invite.email = email
        invite.insert(ignore_permissions=True)