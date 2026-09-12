# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re
from contextlib import contextmanager

import frappe
import requests
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils.html_utils import sanitize_html
from frappe.utils.telemetry import capture

from insights.utils import DocShare, File, get_app_url

# a filter links a column as "links": { '<chart>': "`<query>`.`<column>`" }
LINK_COLUMN = re.compile(r"^`([^`]+)`\.`([^`]+)`$")


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
        permission_user: DF.Link | None
        preview_image: DF.Data | None
        share_link: DF.Data | None
        title: DF.Data | None
        vertical_compact_layout: DF.Check
        workbook: DF.Link
    # end: auto-generated types

    def before_validate(self):
        self.sanitize_text_items()
        # linked_charts is derived from items, so build it before anything
        # validates it - validate() runs before before_save()
        self.set_linked_charts()

    def sanitize_text_items(self):
        """A text item is authored as rich text and rendered as HTML.

        The framework sanitizes the fields it knows carry markup, and `items`
        is a JSON field, so nothing reaches inside it. Sanitizing on the way in
        makes the stored text safe for every reader of the dashboard, including
        the Guest who follows a public link.
        """
        items = frappe.parse_json(self.items) or []
        sanitized = False
        for item in items:
            if item.get("type") != "text" or not item.get("text"):
                continue
            clean = sanitize_html(item["text"], always_sanitize=True)
            sanitized = sanitized or clean != item["text"]
            item["text"] = clean

        if sanitized:
            self.items = items

    def validate(self):
        from insights.permissions import check_dashboard_chart_access

        check_dashboard_chart_access(self)

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
        d.has_workbook_access = frappe.has_permission("Insights Workbook", ptype="read", doc=self.workbook)
        return d

    def after_insert(self):
        # A dashboard created already populated (e.g. imported from a template) is
        # never saved again, so before_save's diff-based preview never runs and it
        # lands without a preview. Generate the initial one here when it has content.
        if frappe.flags.in_patch or not frappe.parse_json(self.items):
            return
        frappe.enqueue_doc(
            doctype=self.doctype,
            name=self.name,
            method="generate_dashboard_preview",
            enqueue_after_commit=True,
        )

    def before_save(self):
        self.enqueue_update_dashboard_preview()

    def set_linked_charts(self):
        """The charts the grid names, once each.

        A Number chart draws one reading per cell, so several cells can name one
        chart. This table answers which charts the dashboard reaches, which is a
        question about charts and not about cells.
        """
        charts = dict.fromkeys(
            item["chart"] for item in frappe.parse_json(self.items) if item["type"] == "chart"
        )
        self.set("linked_charts", [{"chart": chart} for chart in charts])

    def filter_source(self, filter_name: str) -> tuple[str, str, str] | None:
        """The chart, query and column a named filter on this dashboard reads.

        The saved items, deliberately. This is what decides which column a
        caller may ask for at all, so it answers from the document rather than
        from the request it is guarding — and a caller that names the filter
        never has to be handed the link that says where it lands.
        """
        items = frappe.parse_json(self.items) or []
        charts = {item.get("chart") for item in items if item.get("type") == "chart"}

        for item in items:
            if item.get("type") != "filter" or item.get("filter_name") != filter_name:
                continue
            for chart, link in (item.get("links") or {}).items():
                match = LINK_COLUMN.match(link or "")
                if match and chart in charts:
                    return chart, *match.groups()

        return None

    @frappe.whitelist()
    def get_distinct_column_values(
        self,
        filter_name: str,
        search_term: str | None = None,
        filter_context: dict | None = None,
    ):
        """The values one of this dashboard's filters offers.

        Who may read this dashboard was settled before this ran — the builder
        reaches it through `run_doc_method`, and a public link through the same
        endpoint's public fallback. The read is the whole gate, so this reaches the
        query's plain method rather than the `Insights User` endpoint.

        `filter_context` is what the rest of the grid currently holds, unrouted:
        the `items`, the `chart` they link by, and the `filters` state. Routing
        happens here for the same reason it does everywhere else. This filter is
        left out of its own list, or picking a second value would be impossible.
        """
        source = self.filter_source(filter_name)
        if not source:
            frappe.throw(
                frappe._("This filter is not available on this dashboard"),
                frappe.PermissionError,
            )
        _chart, query, column_name = source

        adhoc_filters = None
        if filter_context:
            adhoc_filters = route_filters(
                filter_context.get("items"),
                filter_context.get("chart"),
                filter_context.get("filters"),
                filter_name,
            )

        doc = frappe.get_cached_doc("Insights Query v3", query)
        return doc.distinct_column_values(column_name, search_term=search_term, adhoc_filters=adhoc_filters)

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
        with generate_preview_key(self.name) as key:
            preview = get_page_preview(
                # The browser runs on the server and carries a preview key, so
                # the page it opens is the site's own, not one a request header
                # named.
                frappe.utils.get_url(
                    get_app_url(f"/shared/dashboard/{self.name}"),
                    allow_header_override=False,
                ),
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
    def update_access(self, data: dict | str):
        if not frappe.has_permission("Insights Dashboard v3", ptype="share", doc=self.name):
            frappe.throw("You do not have permission to share this dashboard")

        data = frappe.parse_json(data)
        is_public = data.get("is_public")
        is_shared_with_organization = data.get("is_shared_with_organization")
        people_with_access = data.get("people_with_access") or []

        # this writes is_public with db_set, so validate() never runs. Check
        # before any share is applied, so a refusal leaves nothing half-done.
        if is_public:
            from insights.permissions import check_dashboard_chart_access

            check_dashboard_chart_access(self)

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

        # a public execution has no caller of its own, so the rows it returns are
        # filtered by whoever published the dashboard
        self.db_set(
            {
                "is_public": is_public,
                "permission_user": frappe.session.user if is_public else None,
            }
        )

        if people_with_access:
            capture("dashboard_shared_with_user", "insights")
        if is_public:
            capture("dashboard_set_public", "insights")


def route_filters(
    items, chart: str, filter_states: dict | None, exclude_filter: str | None = None
) -> dict | None:
    """Dashboard filter state, routed to the queries the filters are linked to.

    One router for every surface. The builder is editing items it has not saved
    yet, so it sends those; a public page sends the items it was given. Routing
    is the same either way, and it belongs on this side: a link names a query
    and a column, and the client never has to take the link apart.

    `exclude_filter` leaves one filter out. A filter offering its own values
    must not narrow them by what it currently holds, or picking a second value
    would be impossible.
    """
    if not filter_states:
        return None

    filters_by_query = {}

    for item in frappe.parse_json(items) or []:
        if item.get("type") != "filter":
            continue

        filter_name = item.get("filter_name")
        if exclude_filter and filter_name == exclude_filter:
            continue

        state = filter_states.get(filter_name) or {}
        if not state.get("operator"):
            continue

        link = (item.get("links") or {}).get(chart)
        match = LINK_COLUMN.match(link) if link else None
        if not match:
            continue

        query, column = match.groups()
        group = filters_by_query.setdefault(
            query, {"type": "filter_group", "logical_operator": "And", "filters": []}
        )
        group["filters"].append(
            {
                "type": "filter",
                "column": {"type": "column", "column_name": column},
                "operator": state["operator"],
                "value": state.get("value"),
            }
        )

    return filters_by_query or None


def get_page_preview(url: str, headers: dict | None = None) -> bytes:
    # Newer Frappe renders previews in-process via headless Chromium — no
    # external service, and the site's own /assets and /files resolve locally.
    # Older versions fall back to the preview_generator HTTP service.
    try:
        from frappe.utils.preview import get_preview_from_url
    except ImportError:
        return get_page_preview_via_service(url, headers)

    return get_preview_from_url(url, wait_for=1000, headers=headers or {}, format="jpeg")


def get_page_preview_via_service(url: str, headers: dict | None = None) -> bytes:
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
def generate_preview_key(dashboard: str):
    """A key that stands in for the viewer of one dashboard, for one render.

    The key names its dashboard, so a leaked key reads that dashboard and the
    charts and queries on it — the same documents the preview image itself
    shows — and nothing else.

    It names its viewer too. The render arrives as Guest, so the rows it draws
    are filtered by the user the key was cut for, and the image shows what that
    user would see.
    """
    try:
        key = frappe.generate_hash()
        frappe.cache.set_value(
            f"insights_preview_key:{key}",
            {"dashboard": dashboard, "user": frappe.session.user},
        )
        yield key
    finally:
        frappe.cache.delete_value(f"insights_preview_key:{key}")
