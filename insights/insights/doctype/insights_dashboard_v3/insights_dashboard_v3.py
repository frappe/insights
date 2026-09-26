# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re
from collections.abc import Callable

import frappe
import requests
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils.html_utils import sanitize_html
from frappe.website.utils import cleanup_page_name

from insights import standard
from insights.insights.doctype.insights_chart_v3.chart_query import (
    config_filter_group,
    derive_operations,
    result_column,
)
from insights.insights.query_utils import transitive_closure
from insights.not_permitted import answers_refusal
from insights.permission_user import runs_as
from insights.preview_key import generate_preview_key
from insights.telemetry import capture, capture_share_granted
from insights.utils import DocShare, File, get_app_url

# a filter links a column as "links": { '<chart>': "`<query>`.`<column>`" }
LINK_COLUMN = re.compile(r"^`([^`]+)`\.`([^`]+)`$")

# Which page the view came from, as `docs/telemetry.md` names them.
VIEW_SURFACES = {"workbook", "shared", "dashboards", "desk"}


class InsightsDashboardv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.core.doctype.has_role.has_role import HasRole
        from frappe.types import DF

        from insights.insights.doctype.insights_dashboard_chart_v3.insights_dashboard_chart_v3 import (
            InsightsDashboardChartv3,
        )

        is_standard: DF.Check
        kept_for_desk: DF.Check
        items: DF.JSON | None
        linked_charts: DF.TableMultiSelect[InsightsDashboardChartv3]
        old_name: DF.Data | None
        preview_image: DF.Data | None
        route: DF.Data | None
        share_link: DF.Data | None
        title: DF.Data | None
        vertical_compact_layout: DF.Check
        visibility: DF.Literal["Private", "Roles", "Everyone", "Public"]
        visible_to_roles: DF.TableMultiSelect[HasRole]
        workbook: DF.Link
    # end: auto-generated types

    def before_validate(self):
        self.sanitize_text_items()
        self.drop_deleted_charts()
        # linked_charts is derived from items, so build it before anything
        # validates it - validate() runs before before_save()
        self.set_linked_charts()

    def drop_deleted_charts(self):
        """Remove cells whose chart no longer exists.

        Deleting a chart removes its cells from every dashboard. A browser tab
        that loaded the grid before the delete still has them, and sends them
        back on save.
        """
        items = frappe.parse_json(self.items) or []
        named = {item.get("chart") for item in items if item.get("type") == "chart"}
        if not named:
            return

        stored = set(
            frappe.get_all("Insights Chart v3", filters={"name": ("in", sorted(named))}, pluck="name")
        )
        if named <= stored:
            return

        self.items = [item for item in items if item.get("type") != "chart" or item.get("chart") in stored]

    def sanitize_text_items(self):
        """A text item is authored as rich text and rendered as HTML.

        The framework sanitizes the fields it knows hold markup, and `items`
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
        from insights.permissions import (
            check_dashboard_chart_access,
            check_dashboard_publishes,
            validate_visibility,
        )

        standard.guard_member(self)
        # copied from the workbook, never from the request. It decides whether
        # the site may change this dashboard
        self.is_standard = standard.is_standard_member(self)
        check_dashboard_chart_access(self)
        validate_visibility(self)
        check_dashboard_publishes(self)

    def on_update(self):
        from insights.permissions import capture_visibility_widened

        standard.export_member(self)
        capture_visibility_widened(self)

    def before_rename(self, old_name, new_name, merge=False):
        standard.guard_member(self)

    def after_rename(self, old_name, new_name, merge=False):
        standard.export_member(self)

    def on_trash(self):
        standard.guard_member(self)

    def after_delete(self):
        standard.export_member(self)

    @frappe.whitelist()
    def track_view(self, surface: str | None = None):
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

        if surface not in VIEW_SURFACES:
            surface = "shared" if frappe.session.user == "Guest" else "workbook"
        capture("dashboard_viewed", interval="1d", surface=surface)

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.items, list):
            self.items = frappe.as_json(self.items)
        return super().get_valid_dict(*args, **kwargs)

    def as_dict(self, *args, **kwargs):
        from insights.permissions import can_share, can_write

        d = super().as_dict(*args, **kwargs)

        d.read_only = not can_write(self)
        d.can_share = can_share(self)
        if d.can_share:
            d.people_with_access = self.get_people_with_access()
        d.has_workbook_access = frappe.has_permission("Insights Workbook", ptype="read", doc=self.workbook)
        return d

    def after_insert(self):
        # A dashboard created already populated (e.g. imported from a file) is
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
        self.set_route()
        self.enqueue_update_dashboard_preview()

    def set_route(self):
        """Set a readable `route` for external links.

        The route comes from the title only when it is empty, so a rename keeps
        published links working. Clear the route to get a new one. A numbered
        suffix keeps it unique. Nothing in the app links by route, so at worst
        a suffix breaks a bookmark.
        """
        route = cleanup_page_name(self.route or self.title)
        if not route:
            return

        self.route = self.unique_route(route)

    def unique_route(self, route: str) -> str:
        """`route` with a numbered suffix, until no other dashboard has it as
        its route or its name.

        A standard workbook names its members with readable slugs, so a route
        can equal another dashboard's name. `resolver.resolve` tries the name
        first. Without the name check, a site dashboard with the same title as
        a shipped one gets a route that opens the shipped one, from every
        workspace sidebar item that links to it.
        """
        candidate, suffix = route, 0
        while self.answered_by_another(candidate):
            suffix += 1
            candidate = f"{route}-{suffix}"

        return candidate

    def answered_by_another(self, route: str) -> bool:
        mine = self.name or ""
        if frappe.db.exists(self.doctype, {"route": route, "name": ("!=", mine)}):
            return True

        return route != mine and bool(frappe.db.exists(self.doctype, route))

    def set_linked_charts(self):
        """The charts the grid names, once each.

        A Number chart shows one reading per cell, so several cells can name one
        chart. This table answers which charts the dashboard reaches, which is a
        question about charts and not about cells.
        """
        charts = dict.fromkeys(
            item["chart"] for item in frappe.parse_json(self.items) if item["type"] == "chart"
        )
        self.set("linked_charts", [{"chart": chart} for chart in charts])

    def routing_table(self) -> str:
        """The `items` to route filters by: the request's, or the stored ones.

        `run_doc_method` builds `self` from the request body, so `self.items`
        is the caller's. For the builder, that is its unsaved grid. A caller who
        may save the dashboard is routed by it. Anyone else is routed by the
        stored items. Otherwise they could send a forged link and narrow a
        filter's values by a column the dashboard does not show.

        The permission check uses the name, not `self`. `has_doc_permission`
        reads `owner` and `__islocal` from the document it gets, and
        `BaseDocument.update` copies both from the request. So
        `self.has_permission` would allow anyone who sends them. This follows
        `insights.api.check_stored_document`: decide against the stored row.
        """
        if frappe.has_permission(self.doctype, ptype="write", doc=self.name):
            return self.items

        return frappe.db.get_value(self.doctype, self.name, "items")

    def lookup_filter(self, filter_name: str, lookup: Callable, missing: Callable):
        """Call `lookup(chart, query, column)` for the first link of the named
        filter that the caller is not refused.

        The stored items, deliberately. This is what decides which column a
        caller may ask for at all, so it is read from the row rather than from
        `self`, which a method call builds out of the request body — and a
        caller that names the filter never has to be handed the link that says
        where it lands.

        The link must name a query the chart reads (`chart_reads`). This holds
        for every caller. A link to any other query would ask about rows this
        dashboard does not show.

        The caller must also be able to read the chart. That covers every query
        the chart reads. The query's own permission is not checked, because a
        reader allowed only by a visibility level has none. `can_read_chart`
        checks the session user, so it runs before `runs_as`. Inside `runs_as`
        it would check the chart's owner. The lookup runs as the chart runs, so
        the values come from the same rows as the card.

        A refused link is skipped like a malformed one, and the next link is
        tried. A link is refused when the caller may not read its chart, or
        when the lookup raises Not Permitted for a table they may not read.

        If every link is refused, that is a refusal, not a missing filter. It
        answers like any other refusal on a dashboard the caller may read: an
        empty list. A filter with no usable link calls `missing()`.
        """
        from insights.not_permitted import NotPermitted, forget_refusal, refuse
        from insights.permissions import can_read_chart

        stored = frappe.db.get_value(self.doctype, self.name, "items")
        items = frappe.parse_json(stored) or []
        charts = {item.get("chart") for item in items if item.get("type") == "chart"}

        refused = False
        for item in items:
            if item.get("type") != "filter" or item.get("filter_name") != filter_name:
                continue
            for chart, link in (item.get("links") or {}).items():
                match = LINK_COLUMN.match(link or "")
                if not match or chart not in charts:
                    continue
                query, column = match.groups()
                if not chart_reads(chart, query):
                    continue
                if not can_read_chart(chart):
                    refused = True
                    continue
                try:
                    with runs_as(frappe.get_doc("Insights Chart v3", chart)):
                        return lookup(chart, frappe.get_cached_doc("Insights Query v3", query), column)
                except NotPermitted as refusal:
                    forget_refusal(refusal)
                    refused = True

        if refused:
            refuse([])

        return missing()

    @frappe.whitelist()
    @answers_refusal(list)
    def get_distinct_column_values(
        self,
        filter_name: str,
        search_term: str | None = None,
        filter_context: dict | None = None,
    ):
        """The values one of this dashboard's filters lists.

        Read access to the dashboard is checked before this runs. The builder
        calls it through `run_doc_method`, and a reader through
        `insights.api.view.get_filter_values`. That check is the only gate, so
        this calls the query's method directly. A reader of this dashboard may
        have no Insights role.

        `answers_refusal` is here because the method is whitelisted. A card
        over a table the caller may not read then answers an empty list, the
        same as through `insights.api.view`.
        """
        adhoc_filters = self._filter_context_filters(filter_name, filter_context)
        return self.lookup_filter(
            filter_name,
            lambda chart, query, column: query.distinct_column_values(
                column, search_term=search_term, adhoc_filters=adhoc_filters
            ),
            missing=filter_not_available,
        )

    def _filter_context_filters(self, filter_name: str, filter_context: dict | None = None):
        """The rest of the grid's filters, routed, to narrow one of this
        dashboard's filters.

        `filter_context` holds the grid's current state, unrouted: the `chart`
        whose links to follow, and the `filters` state. This filter is left
        out, or a second value could never be picked.

        The links come from `routing_table`, not from `filter_context`. A link
        names a query and a column, and a forged one would narrow this list by
        a column the dashboard does not show.
        """
        if not filter_context:
            return None

        return route_filters(
            self.routing_table(),
            filter_context.get("chart"),
            filter_context.get("filters"),
            filter_name,
        )

    @frappe.whitelist()
    @answers_refusal(lambda: None)
    def get_filter_column_range(self, filter_name: str, filter_context: dict | None = None):
        """The range one of this dashboard's own filters allows.

        Addressed and routed the way `get_distinct_column_values` is: the preset
        ranges a picker shows and the values it lists answer the same question
        about the same rows.
        """
        adhoc_filters = self._filter_context_filters(filter_name, filter_context)
        return self.lookup_filter(
            filter_name,
            lambda chart, query, column: query.column_range(column, adhoc_filters=adhoc_filters),
            missing=filter_not_available,
        )

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
                # The browser runs on the server and passes a preview key, so
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

    def get_people_with_access(self):
        DocShare = frappe.qb.DocType("DocShare")
        User = frappe.qb.DocType("User")

        return (
            frappe.qb.from_(DocShare)
            .left_join(User)
            .on(DocShare.user == User.name)
            .select(
                User.full_name,
                User.user_image,
                User.email,
            )
            .where(DocShare.share_doctype == "Insights Dashboard v3")
            .where(DocShare.share_name == self.name)
            .where(DocShare.user.isnotnull())
            .where((DocShare.read == 1) | (DocShare.write == 1))
            .run(as_dict=True)
        )

    @frappe.whitelist()
    def update_access(self, data: dict | str):
        """Share this dashboard with exactly the listed users.

        This only adds and removes shares. `visibility` is a separate field
        that the dialog saves with the document. `validate_shareable_users`
        decides who may be in the list, as it does for workbook shares. Without
        it, only the client's user picker stopped a share to a portal user, who
        could then download the owner's rows.
        """
        from insights.permissions import validate_shareable_users

        if not frappe.has_permission("Insights Dashboard v3", ptype="share", doc=self.name):
            frappe.throw("You do not have permission to share this dashboard")

        data = frappe.parse_json(data)
        people_with_access = data.get("people_with_access") or []

        existing_shares = frappe.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Dashboard v3",
                "share_name": self.name,
                "read": 1,
            },
            fields=["name", "user"],
        )
        # the dialog sends back every existing share, so check only new users.
        # Otherwise an old share, made before this check or to a user who has
        # since left Insights, would block every later save
        validate_shareable_users(set(people_with_access) - {share.user for share in existing_shares})

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

        newly_shared = set(people_with_access) - set(existing_share_users)
        if newly_shared:
            capture_share_granted("dashboard", "user", len(newly_shared))


def filter_not_available():
    frappe.throw(
        frappe._("This filter is not available on this dashboard"),
        frappe.PermissionError,
    )


# The two operators that ask about the column itself, so they stand without a value.
VALUELESS_OPERATORS = ("is_set", "is_not_set")


def _filter_is_set(state: dict) -> bool:
    """Whether a filter's state says enough to run.

    A filter picked an operator and not yet a value is the normal half-filled
    state of the picker, and routing it would narrow every chart on the page by
    a comparison against nothing.
    """
    operator = state.get("operator")
    if not operator:
        return False
    if operator in VALUELESS_OPERATORS:
        return True
    return state.get("value") not in (None, "", [])


def chart_reads(chart: str, query: str) -> bool:
    """Whether a filter on `chart` may link to `query`: the chart's query, or
    one it reads.

    `route_filters` keys each filter group by the query its link names, and
    the build applies the group when it reaches that query. A link to a query
    the chart does not read changes nothing on the chart. But a filter's value
    lookup would still run that query, as the chart runs, over rows the
    dashboard does not show.

    Anyone who may save the dashboard can write links, and an `edit` share on
    the workbook gives that to every member. So this is checked where a link
    is followed, not where it is saved.
    """
    source = frappe.db.get_value("Insights Chart v3", chart, "query")
    if not source:
        return False

    return query == source or query in transitive_closure(source)


def route_filters(
    items, chart: str, filter_states: dict | None, exclude_filter: str | None = None
) -> dict | None:
    """Dashboard filter state, routed to the queries the filters are linked to.

    Every caller routes through here. For a reader, the saved dashboard's
    items are passed. The builder passes its unsaved items. Routing runs on the
    server because a link names a query and a column, and a reader is never
    sent those.

    `exclude_filter` leaves one filter out. A filter listing its own values
    must not narrow them by what it currently holds, or picking a second value
    would be impossible.
    """
    filters_by_query = {}

    for _, query, column, state in routed_filter_links(items, chart, filter_states, exclude_filter):
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


def routed_filter_links(items, chart: str, filter_states: dict | None, exclude_filter: str | None = None):
    """Yield `(filter name, query, column, state)` for each set dashboard
    filter linked to `chart`."""
    if not filter_states:
        return

    for item in frappe.parse_json(items) or []:
        if item.get("type") != "filter":
            continue

        filter_name = item.get("filter_name")
        if exclude_filter and filter_name == exclude_filter:
            continue

        state = filter_states.get(filter_name) or {}
        if not _filter_is_set(state):
            continue

        link = (item.get("links") or {}).get(chart)
        match = LINK_COLUMN.match(link) if link else None
        if match:
            yield filter_name, *match.groups(), state


def card_filter_source(chart: str, column: str) -> tuple[str | None, str | None, dict | None]:
    """Where a card filter lands: the card's query, the source column the named
    column reads, and the narrowing the card itself already applies.

    The card's own operations answer all three, so every chart type is read the
    same way. Its aggregating operation names every column the chart holds
    (the dimensions it groups by, under the names they come back as, and the
    measures it states), and a column no operation names is not one the card
    shows. That is a
    `None` query, which is what the caller refuses.

    A dimension reads a source column, and that column is where its values come
    from. A measure reads none: it is computed over the result, and so is every
    column a pivot makes. Both are shown and list no values, which is what a
    source column of `None` says. A pivot names its columns after the values its
    data holds, so on a pivoted card that is the answer for every column the
    config does not name.

    The card's own filters come back with it because a list showing what the
    card does not show reaches past what the chart published.
    """
    query, chart_type, config = frappe.db.get_value(
        "Insights Chart v3", chart, ["query", "chart_type", "config"]
    ) or (None, None, None)
    if not query:
        return None, None, None

    config = frappe.parse_json(config or "{}")
    filter_group = config_filter_group(config)
    card_filters = {query: filter_group} if filter_group else None

    for operation in derive_operations(chart_type, query, config):
        if operation["type"] == "summarize":
            dimensions, measures = operation["dimensions"], operation["measures"]
        elif operation["type"] == "pivot_wider":
            dimensions, measures = [*operation["rows"], *operation["columns"]], operation["values"]
        else:
            continue

        for dimension in dimensions:
            if dimension and result_column(dimension) == column:
                check_card_filter(chart)
                return query, dimension.get("column_name"), card_filters

        if any(measure and measure.get("measure_name") == column for measure in measures):
            return query, None, card_filters

        if operation["type"] == "pivot_wider":
            return query, None, card_filters

    return None, None, None


def can_filter_card(chart: str) -> bool:
    """Whether the reader may add their own filter to the card.

    A card filter cuts the chart's rows another way, as a drill breakdown
    does, so `can_read_rows` decides. Dashboard filters are set by the author
    and go through `route_filters` instead.
    """
    from insights.permissions import can_read_rows

    return can_read_rows(frappe._dict(doctype="Insights Chart v3", name=chart))


def check_card_filter(chart: str) -> None:
    from insights.not_permitted import refuse

    if not can_filter_card(chart):
        refuse(message=frappe._("This chart shows only what its owner saved, so it cannot be filtered"))


def route_card_filters(chart: str, card_filters: list | None, adhoc_filters: dict | None) -> dict | None:
    """The reader's own filters on one card, landing on the card's own query.

    A card filter is the reader's and not the author's: it names a column the
    card shows and reaches no further, so it is taken from the request whole on
    every surface, public included. It lands under the chart's own name, which is
    what the chart's derived query is called, so the rule falls after the chart's
    summarize — on the columns the card shows, measures included.
    """
    rules = []
    for card_filter in frappe.parse_json(card_filters) or []:
        column = card_filter.get("column")
        operator = card_filter.get("operator")
        if not column or not isinstance(column, str) or not operator:
            continue
        rules.append(
            {
                "type": "filter",
                "column": {"type": "column", "column_name": column},
                "operator": operator,
                "value": card_filter.get("value"),
            }
        )

    if not rules:
        return adhoc_filters

    check_card_filter(chart)
    routed = dict(adhoc_filters or {})
    group = routed.setdefault(chart, {"type": "filter_group", "logical_operator": "And", "filters": []})
    group["filters"] = [*group["filters"], *rules]
    return routed


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
