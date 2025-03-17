# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re
from contextlib import contextmanager

import frappe
import requests
from frappe.model.document import Document

from insights.utils import File


class InsightsDashboardv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        is_public: DF.Check
        items: DF.JSON | None
        linked_charts: DF.JSON | None
        old_name: DF.Data | None
        preview_image: DF.Data | None
        share_link: DF.Data | None
        title: DF.Data | None
        workbook: DF.Link
    # end: auto-generated types

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.items, list):
            self.items = frappe.as_json(self.items)
        if isinstance(self.linked_charts, list):
            self.linked_charts = frappe.as_json(self.linked_charts)
        return super().get_valid_dict(*args, **kwargs)

    def before_save(self):
        self.set_linked_charts()
        self.enqueue_update_dashboard_preview()

    def set_linked_charts(self):
        linked_charts = []
        for item in frappe.parse_json(self.items):
            if item["type"] == "chart":
                linked_charts.append(item["chart"])
        self.linked_charts = linked_charts

    @frappe.whitelist(allow_guest=True)
    def get_distinct_column_values(self, query, column_name, search_term=None):
        is_guest = frappe.session.user == "Guest"
        if not is_guest and not self.is_public:
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
        if self.is_new() or not self.get_doc_before_save():
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

    @frappe.whitelist()
    def get_shared_with(self):
        DocShare = frappe.qb.DocType("DocShare")
        User = frappe.qb.DocType("User")

        shared_with = (
            frappe.qb.from_(DocShare)
            .left_join(User)
            .on(DocShare.user == User.name)
            .select(
                DocShare.user,
                User.full_name,
                User.user_image,
                User.email,
            )
            .where(DocShare.share_doctype == "Insights Dashboard v3")
            .where(DocShare.share_name == self.name)
            .where(DocShare.read == 1)
            .run(as_dict=True)
        )
        return shared_with

    @frappe.whitelist()
    def update_shared_with(self, users):
        if not frappe.has_permission(
            "Insights Dashboard v3", ptype="share", doc=self.name
        ):
            frappe.throw("You do not have permission to share this dashboard")

        existing_shares = frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Dashboard v3",
                "share_name": self.name,
                "read": 1,
                "user": ["in", users],
            },
            fields=["name", "user"],
        )

        # remove all existing shares that are not in the new list
        for share in existing_shares:
            if share.user not in users:
                frappe.delete_doc("DocShare", share.name)

        # add new shares
        for user in users:
            if user not in [share.user for share in existing_shares]:
                frappe.get_doc(
                    {
                        "doctype": "DocShare",
                        "share_doctype": "Insights Dashboard v3",
                        "share_name": self.name,
                        "user": user,
                        "read": 1,
                        "notify_by_email": 0,
                    }
                ).insert()


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
