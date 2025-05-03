# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re
from contextlib import contextmanager

import frappe
import requests
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now

from insights.utils import DocShare, File


class InsightsDashboardv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from insights.insights.doctype.insights_dashboard_chart_v3.insights_dashboard_chart_v3 import (
            InsightsDashboardChartv3,
        )

        is_public: DF.Check
        items: DF.JSON | None
        linked_charts: DF.TableMultiSelect[InsightsDashboardChartv3]
        old_name: DF.Data | None
        preview_image: DF.Data | None
        share_link: DF.Data | None
        title: DF.Data | None
        workbook: DF.Link
    # end: auto-generated types

    @frappe.whitelist()
    def track_view(self):
        view_log = frappe.qb.DocType("View Log")
        last_viewed_recently = frappe.db.get_value(
            view_log,
            filters=(
                (view_log.creation > (Now() - Interval(minutes=5)))
                & (view_log.reference_doctype == self.doctype)
                & (view_log.reference_name == self.name)
                & (view_log.viewed_by == frappe.session.user)
            ),
            pluck="name",
        )
        if not last_viewed_recently:
            self.add_viewed(force=True)

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.items, list):
            self.items = frappe.as_json(self.items)
        return super().get_valid_dict(*args, **kwargs)

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)

        d.read_only = not self.has_permission("write")
        if not d.read_only:
            access = self.get_acess_data()
            d.people_with_access = access[0]
            d.is_shared_with_organization = access[1]

        return d

    def before_save(self):
        self.set_linked_charts()
        self.enqueue_update_dashboard_preview()

    def set_linked_charts(self):
        self.set(
            "linked_charts",
            [
                {"chart": item["chart"]}
                for item in frappe.parse_json(self.items)
                if item["type"] == "chart"
            ],
        )

    @frappe.whitelist()
    def get_distinct_column_values(self, query, column_name, search_term=None):
        is_guest = frappe.session.user == "Guest"
        if is_guest and not self.is_public:
            raise frappe.PermissionError

        self.check_linked_filters(query, column_name)

        doc = frappe.get_cached_doc("Insights Query v3", query)
        return doc.get_distinct_column_values(column_name, search_term=search_term)

    def check_linked_filters(self, query, column_name):
        items = frappe.parse_json(self.items)
        filters = [item for item in items if item["type"] == "filter"]
        for f in filters:
            # check if there is a filter which has "link": { 'chart': "`<query>`.`<column>`" }
            linked_columns = f.get("links", {}).values()
            pattern = "^`([^`]+)`\\.`([^`]+)`$"
            for linked_column in linked_columns:
                match = re.match(pattern, linked_column)
                if (
                    match
                    and match.groups()[0] == query
                    and match.groups()[1] == column_name
                ):
                    return True

        raise frappe.PermissionError

    def enqueue_update_dashboard_preview(self):
        if self.is_new() or not self.get_doc_before_save() or frappe.flags.in_patch:
            return

        prev_doc = self.get_doc_before_save()
        frappe.enqueue_doc(
            doctype=self.doctype,
            name=self.name,
            method="update_dashboard_preview",
            new_doc=self.as_dict(),
            prev_doc=prev_doc.as_dict(),
            enqueue_after_commit=True,
        )

    def update_dashboard_preview(self, new_doc, prev_doc):
        new_doc = frappe.parse_json(new_doc)
        prev_doc = frappe.parse_json(prev_doc)

        if new_doc["items"] == prev_doc["items"]:
            return

        self.generate_dashboard_preview()

    def generate_dashboard_preview(self):
        with generate_preview_key() as key:
            preview = get_page_preview(
                frappe.utils.get_url(f"/insights/shared/dashboard/{self.name}"),
                headers={
                    "X-Insights-Preview-Key": key,
                },
            )
            file_url = create_preview_file(preview, self.name)
            random_hash = frappe.generate_hash()[0:4]
            file_url = f"{file_url}?{random_hash}"
            self.db_set("preview_image", file_url)
            return file_url

    def get_acess_data(self):
        DocShare = frappe.qb.DocType("DocShare")
        User = frappe.qb.DocType("User")

        shared_with = (
            frappe.qb.from_(DocShare)
            .left_join(User)
            .on(DocShare.user == User.name)
            .select(
                DocShare.user,
                DocShare.everyone,
                User.full_name,
                User.user_image,
                User.email,
            )
            .where(DocShare.share_doctype == "Insights Dashboard v3")
            .where(DocShare.share_name == self.name)
            .where((DocShare.read == 1) | (DocShare.write == 1))
            .run(as_dict=True)
        )

        org_access = False
        people_with_access = []
        for share in shared_with:
            if not share.everyone:
                people_with_access.append(
                    {
                        "full_name": share.full_name,
                        "user_image": share.user_image,
                        "email": share.email,
                    }
                )
            else:
                org_access = True

        return people_with_access, org_access

    @frappe.whitelist()
    def update_access(self, data):
        if not frappe.has_permission(
            "Insights Dashboard v3", ptype="share", doc=self.name
        ):
            frappe.throw("You do not have permission to share this dashboard")

        data = frappe.parse_json(data)
        is_public = data.get("is_public")
        is_shared_with_organization = data.get("is_shared_with_organization")
        people_with_access = data.get("people_with_access") or []

        existing_shares = frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Dashboard v3",
                "share_name": self.name,
                "read": 1,
            },
            fields=["name", "user", "everyone"],
        )

        # remove all existing shares that are not in the new list
        for share in existing_shares:
            if share.user and share.user not in people_with_access:
                frappe.delete_doc("DocShare", share.name, ignore_permissions=True)

        # add new shares
        existing_share_users = [share.user for share in existing_shares if share.user]
        for user in people_with_access:
            if user not in existing_share_users:
                doc = DocShare.get_or_create_doc(
                    share_doctype="Insights Dashboard v3",
                    share_name=self.name,
                    user=user,
                )
                doc.read = 1
                doc.notify_by_email = 0
                doc.save(ignore_permissions=True)

        org_shares = [share for share in existing_shares if share.everyone]
        if is_shared_with_organization and not org_shares:
            doc = DocShare.get_or_create_doc(
                share_doctype="Insights Dashboard v3",
                share_name=self.name,
                everyone=1,
            )
            doc.read = 1
            doc.notify_by_email = 0
            doc.save(ignore_permissions=True)
        elif org_shares and not is_shared_with_organization:
            for share in org_shares:
                frappe.delete_doc("DocShare", share.name, ignore_permissions=True)

        self.db_set("is_public", is_public)


def get_page_preview(url: str, headers: dict | None = None) -> bytes:
    PREVIEW_GENERATOR_URL = (
        frappe.conf.preview_generator_url
        or "https://preview.frappe.cloud/api/method/preview_generator.api.generate_preview_from_url"
    )

    response = requests.post(
        PREVIEW_GENERATOR_URL,
        json={
            "url": url,
            "headers": headers or {},
            "wait_for": 1000,
        },
    )
    if response.status_code == 200:
        return response.content
    else:
        exception = response.json()
        frappe.log_error(message=exception, title="Failed to generate preview")
        frappe.throw("Failed to generate preview")


def create_preview_file(content: bytes, dashboard_name: str):
    file_name = f"{dashboard_name}-preview.jpeg"
    file = File.get_or_create_doc(
        attached_to_doctype="Insights Dashboard v3",
        attached_to_name=dashboard_name,
        file_name=file_name,
        is_private=1,
    )
    if file.name:
        file.content = content
        file.save_file(overwrite=True)
        file.save()
    else:
        # insert file while ensuring file name is same as the one we want
        # first insert without content to reserve the file name (ignoring validate_file_on_disk)
        # then overwrite the file with the content
        file.flags.ignore_validate = True
        file.insert()
        file.flags.ignore_validate = False
        file.content = content
        file.save_file(overwrite=True)
        file.save()

    return file.file_url


@contextmanager
def generate_preview_key():
    try:
        key = frappe.generate_hash()
        frappe.cache.set_value(f"insights_preview_key:{key}", True)
        yield key
    finally:
        frappe.cache.delete_value(f"insights_preview_key:{key}")
