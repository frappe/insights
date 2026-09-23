# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, getdate

from insights import standard, user_permissions
from insights.desk import claims_on, refuse_delete_while_claimed
from insights.insights.doctype.insights_chart_v3.chart_drill import check_rows
from insights.insights.doctype.insights_chart_v3.chart_query import (
    column_granularity,
    comparison_sources,
    comparison_timespans,
    config_errors,
    derive_operations,
    grain_step,
    normalize_chart_config,
    period_column,
    period_grain,
    reads_newest_first,
    sparkline_operations,
)
from insights.insights.doctype.insights_chart_v3.record_link import record_links
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import route_card_filters
from insights.insights.doctype.insights_query_v3.insights_query_v3 import import_query
from insights.insights.query_builders.sql_functions import reading_day, resolve_timespan
from insights.permission_user import runs_as
from insights.permissions import can_export, can_read_rows
from insights.utils import deep_convert_dict_to_dict, refuse_delete_while_linked

QUERY = "Insights Query v3"

# A page of an ascending series ends at its oldest rows, so a series cut by the
# card's own page size would stop short of the number it is drawn under. This is
# the bound instead: more periods than any period a card is read over.
SPARKLINE_MAX_POINTS = 1000


class InsightsChartv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.core.doctype.has_role.has_role import HasRole
        from frappe.types import DF

        chart_type: DF.Data | None
        config: DF.JSON | None
        folder: DF.Data | None
        is_standard: DF.Check
        kept_for_desk: DF.Check
        old_name: DF.Data | None
        query: DF.Link | None
        run_as_owner: DF.Check
        sort_order: DF.Int
        title: DF.Data | None
        visibility: DF.Literal["Private", "Roles", "Everyone", "Public"]
        visible_to_roles: DF.TableMultiSelect[HasRole]
        workbook: DF.Link
    # end: auto-generated types

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.config, dict):
            self.config = frappe.as_json(self.config)
        return super().get_valid_dict(*args, **kwargs)

    def as_dict(self, *args, **kwargs):
        from insights.permissions import can_share, can_write, may_move_run_as_owner

        d = super().as_dict(*args, **kwargs)
        d.read_only = not can_write(self)
        d.can_share = can_share(self)
        d.can_move_run_as_owner = may_move_run_as_owner(self)
        return d

    def validate(self):
        from insights.permissions import (
            check_chart_query_access,
            check_trusted_code_author,
            validate_run_as_owner,
            validate_visibility,
        )

        standard.guard_member(self)
        before = self.get_doc_before_save()
        check_trusted_code_author([(self.title, self.config, before and before.config)])
        # a copy of the workbook's flag, so the workbook writes it and a request
        # never does - it decides a read past the site's team grants
        self.is_standard = standard.is_standard_member(self)
        check_chart_query_access(self)
        validate_visibility(self)
        validate_run_as_owner(self)
        self.normalize_config()

    def normalize_config(self):
        """The config stored in the shape every reader reads, whoever wrote it.

        The builder is one writer of a config. A workbook import and a file
        another app ships are the others, and either can deliver a shape an
        older release wrote. Every one of them arrives here, so this is where an
        older shape stops being stored.
        """
        config = frappe.parse_json(self.config)
        if isinstance(config, dict):
            self.config = normalize_chart_config(config, self.chart_type)

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
        if not self.flags.force_delete:
            refuse_delete_while_claimed(self.title or self.name, claims_on(self.doctype, {"name": self.name}))
            refuse_delete_while_linked(self, taken=("Insights Dashboard v3",))
        self.remove_from_dashboards()

        # Clean up empty folders
        if self.folder:
            self.cleanup_empty_folder(self.folder)

    def remove_from_dashboards(self):
        """Take this chart's cells, and the filter links to it, off every dashboard.

        A dashboard's grid links the chart, so the framework refuses the delete
        while any cell names it - and a chart in use would never be removable.
        """
        dashboards = frappe.get_all(
            "Insights Dashboard Chart v3",
            filters={"chart": self.name, "parenttype": "Insights Dashboard v3"},
            pluck="parent",
            distinct=True,
        )
        for name in dashboards:
            dashboard = frappe.get_doc("Insights Dashboard v3", name)
            items = []
            for item in frappe.parse_json(dashboard.items) or []:
                if item.get("type") == "chart" and item.get("chart") == self.name:
                    continue
                if item.get("type") == "filter":
                    (item.get("links") or {}).pop(self.name, None)
                items.append(item)
            dashboard.items = frappe.as_json(items)
            dashboard.save(ignore_permissions=True)

    def after_delete(self):
        standard.export_member(self)

    def cleanup_empty_folder(self, folder_name):
        """Delete folder if it has no queries or charts"""
        if not frappe.db.exists("Insights Folder", folder_name):
            return

        folder = frappe.get_doc("Insights Folder", folder_name)
        folder_type = folder.type

        if folder_type == "query":
            has_items = frappe.db.exists("Insights Query v3", {"folder": folder_name})
        else:
            has_items = frappe.db.exists("Insights Chart v3", {"folder": folder_name})

        if not has_items:
            frappe.delete_doc("Insights Folder", folder_name, force=True, ignore_permissions=True)

    def fetch(
        self,
        force: bool = False,
        adhoc_filters: dict | None = None,
        card_filters: list | None = None,
        page: int = 1,
    ):
        """Fetch this chart's rows under the permissions declared on this document.

        The stored chart is re-read, so it alone decides whose permissions apply
        and the query that runs under them. A page is as long as the `limit` its
        author saved, and the first page is the picture: a later one is for a
        caller `can_read_rows` admits, and anyone else is answered the first.

        Filter state arrives routed, keyed by the queries the links name.

        `card_filters` is the reader's own filter on this one card. It names a
        column the card draws, and it lands on the card's own derived query, so
        it is taken from the request on every surface.

        A span card's sparkline comes back under `sparkline`. It runs here
        and not through a call of its own so that a client never has to know
        which cards need a second fetch, and so that a filter cannot reach one
        execution and miss the other.
        """
        chart = frappe.get_doc(self.doctype, self.name)
        if not can_read_rows(chart):
            page = 1
        page_size = frappe.parse_json(chart.config or "{}").get("limit") or 100
        # the day every span in this read resolves against. A drill carries it
        # back, so what is behind the number is cut for the day it was read
        drawn_on = str(getdate(reading_day()))
        adhoc_filters = route_card_filters(self.name, card_filters, adhoc_filters)

        query = chart.get_query()
        with runs_as(chart):
            result = query.execute(
                force=force,
                page=page,
                page_size=page_size,
                adhoc_filters=adhoc_filters,
            )
            # read before the sparkline runs: a second build answers for itself.
            # For the reader at the keyboard only - a chart that ran as its owner
            # narrowed by the owner's grants, which name documents this reader
            # was never published and a restriction they do not hold
            scope = user_permissions.scope(frappe.session.user)
            sparkline = chart.get_sparkline_data(force=force, adhoc_filters=adhoc_filters)
        # A reading surface answers with rows and nothing about how they were
        # fetched. The SQL names tables, joins and columns the reader was never
        # published, and `insights.api.view` opens this to a guest.
        result.pop("sql", None)

        result["rows"] = chart.periods_oldest_last(result["rows"])

        # the client formats and links by these, and a reading surface is the
        # only place it can learn them
        operations = chart.get_operations()
        result["granularity"] = column_granularity(operations)
        if links := record_links(operations, result["columns"]):
            result["record_links"] = links

        # what of the reader's own narrowed these rows. A scoped number reads as
        # the whole one, so the card has to be able to say
        result["scope"] = scope

        if sparkline:
            result["sparkline"] = sparkline
        if rows := chart.comparison_rows(result["rows"]):
            result["comparison_rows"] = rows
        result["drawn_on"] = drawn_on
        return result

    def count_rows(
        self,
        adhoc_filters: dict | None = None,
        card_filters: list | None = None,
        force: bool = False,
    ) -> int:
        """How many rows the pages of `fetch` are cut from, under the same filters.

        More than the picture, so only for a caller `can_read_rows` admits. Asked
        of this document, which a view reads from its row and the builder
        builds from the shape it is editing.
        """
        check_rows(self)
        adhoc_filters = route_card_filters(self.name, card_filters, adhoc_filters)
        with runs_as(self):
            return self.get_query().count_rows(adhoc_filters=adhoc_filters, force=force)

    def export_rows(
        self,
        format: str = "csv",
        adhoc_filters: dict | None = None,
        card_filters: list | None = None,
    ) -> str:
        """Every row the pages of `fetch` are cut from, as a file, under the same filters.

        The chart's own rows, summarized as it draws them, not the rows of the
        query it reads. `can_export` decides, and a refusal raises: a file is an
        act, not a picture.
        """
        if not can_export(self):
            frappe.throw(_("You are not allowed to download data"), exc=frappe.PermissionError)
        adhoc_filters = route_card_filters(self.name, card_filters, adhoc_filters)
        with runs_as(self):
            return self.get_query().export_rows(format, adhoc_filters=adhoc_filters)

    def periods_oldest_last(self, rows: list[dict]) -> list[dict]:
        """The rows the card reads, in the order every reader expects them.

        A grain card is fetched newest first so the periods it reads are on the
        first page, and the page is turned back over here: the reading is the
        last row, and the comparison is read against a row of that same list.
        """
        config = frappe.parse_json(self.config or "{}")
        return list(reversed(rows)) if reads_newest_first(self.chart_type, config) else rows

    def comparison_rows(self, rows: list[dict]) -> dict[str, int | None]:
        """Which row answers each comparison, keyed by the source that asks it.

        A reading is measured against a row of its own, so two readings asking
        different questions read different rows. Counting back from the end
        cannot say which is which: a card fetches one stretch per distinct
        comparison, and they come back oldest first, each named by the date it
        starts on.

        Answered here because the answer is a date. A span carries none until
        the query runs, and the same span resolved a second time in the browser
        would be resolved against a different clock and a different fiscal
        calendar.

        A grain period fetches nothing beside itself, since every period it has
        is already a row. The period before this one is the last row's period
        stepped back one grain, looked up by its date: the row before the last
        is some earlier period when the data has a gap. That is the whole of
        what a grain can answer.

        A source with no row to read is named with `None`: the question stands
        and the card prints it with no figure. A source that is missing is one
        this period cannot be asked at all.
        """
        if self.chart_type != "Number" or not rows:
            return {}

        config = frappe.parse_json(self.config or "{}")
        column = period_column(self.chart_type, config)
        timespans = comparison_timespans(self.chart_type, config)
        if not timespans:
            if "previous" not in comparison_sources(self.chart_type, config):
                return {}
            grain = period_grain(self.chart_type, config)
            last = rows[-1].get(column)
            if not grain or not last:
                return {"previous": None}
            starts = {get_datetime(row[column]): index for index, row in enumerate(rows) if row.get(column)}
            back = {unit: -count for unit, count in grain_step(grain).items()}
            return {"previous": starts.get(add_to_date(get_datetime(last), **back))}

        starts = {getdate(row[column]): index for index, row in enumerate(rows) if row.get(column)}

        return {source: starts.get(resolve_timespan(timespan)[0]) for source, timespan in timespans.items()}

    def get_sparkline_data(self, force: bool = False, adhoc_filters: dict | None = None):
        """The series behind this card's sparkline, or nothing when it draws none.

        Only a card that asks for both a sparkline and a span runs it. Execution
        is limited rather than queued (a dashboard already fills the pool), so a
        second execution per card stays something an author turns on.
        """
        operations = sparkline_operations(self.chart_type, self.query, frappe.parse_json(self.config or "{}"))
        if not operations:
            return None

        result = self.get_query(operations=operations).execute(
            force=force,
            page_size=SPARKLINE_MAX_POINTS,
            adhoc_filters=adhoc_filters,
        )
        return {"columns": result["columns"], "rows": result["rows"]}

    def last_modified(self) -> str | None:
        """The newest `modified` of the stored chart this names and every query it reads.

        A drill carries it back from the card and is refused once it moved: the
        drill cuts the queries as they are now, and an edit to any of them puts
        new rows under the old number. Read by name, so the builder's preview of
        a saved chart answers with that chart's version, and the config on the
        wire, the author's own, is not part of it. Nothing for a name no chart
        holds.
        """
        stored = frappe.db.get_value(self.doctype, self.name, ["modified", "query"], as_dict=True)
        if not stored:
            return None

        from insights.insights.query_utils import transitive_closure

        queries = {stored.query, *transitive_closure(stored.query)} if stored.query else set()
        modified = frappe.get_all(QUERY, filters={"name": ["in", list(queries)]}, pluck="modified")
        return str(max([stored.modified, *modified]))

    def get_query(self, operations: list | None = None):
        """A query document for this chart's operations, made to run and thrown away.

        Nothing about it is worth keeping: the operations follow from the config, so
        the config is the only copy. It is never inserted, and it names the source
        query as its execution reference so a chart run still counts as usage of the
        tables it read.

        `operations` runs something built out of the chart's own instead — a drill's
        cut pipeline, against the same source and connection the chart uses.
        """
        query = frappe.new_doc(QUERY)
        query.name = self.name
        query.title = self.title
        query.workbook = self.workbook
        query.operations = frappe.as_json(self.get_operations() if operations is None else operations)
        source = (
            frappe.db.get_value(
                QUERY,
                self.query,
                ["use_live_connection", "is_native_query", "is_script_query", "is_builder_query"],
                as_dict=True,
            )
            or frappe._dict()
        )
        # a chart run belongs to the editor its source query was written in, which
        # is what a failure report names it by
        query.use_live_connection = source.use_live_connection
        query.is_native_query = source.is_native_query
        query.is_script_query = source.is_script_query
        query.is_builder_query = source.is_builder_query
        query.flags.execution_reference = self.query
        return query

    def get_operations(self):
        """The operations that produce the chart's rows.

        The source query, the chart's own filters, its summarize or pivot, and its
        sort, derived here from the config every time the chart runs. A config
        that cannot be drawn is an error, not a row set: falling back to the source
        query would draw its raw rows under the chart's title.
        """
        config = frappe.parse_json(self.config or "{}")
        errors = config_errors(self.chart_type, self.query, config)
        if errors:
            frappe.throw(
                _("Chart {0} is not configured: {1}. Open it in Insights to configure it.").format(
                    frappe.bold(self.title or self.name), ", ".join(errors)
                ),
                title=_("Chart is not configured"),
            )

        return derive_operations(self.chart_type, self.query, config)

    @frappe.whitelist()
    def published_reach(self):
        """See `insights.permissions.published_reach`."""
        from insights.permissions import published_reach

        return published_reach(self)

    @frappe.whitelist()
    def export(self):
        from insights.permissions import check_referenced_query_access

        chart = {
            "version": "1.0",
            "timestamp": frappe.utils.now(),
            "type": "Chart",
            "name": self.name,
            "doc": {
                "name": self.name,
                "title": self.title,
                "workbook": self.workbook,
                "query": self.query,
                "chart_type": self.chart_type,
                "config": frappe.parse_json(self.config),
            },
            "dependencies": {
                "queries": {},
            },
        }

        check_referenced_query_access(self.query)
        exported_query = frappe.get_doc("Insights Query v3", self.query).export()
        chart["dependencies"]["queries"][self.query] = exported_query

        return chart

    @frappe.whitelist()
    def duplicate(self):
        """A copy of this chart, published to nobody yet.

        `copy_doc` carries every field that is not `no_copy`, and the declared
        visibility is one of them. A copy is a new document, so nobody's reach
        moved - but it would arrive at a level its own author may never have
        been able to publish, and `validate_visibility` reads a new document at
        any level as a widening. The copy starts where a new chart starts.
        """
        from insights.permissions import PRIVATE

        new_chart = frappe.copy_doc(self)
        new_chart.title = f"{self.title} (Copy)"
        new_chart.visibility = PRIVATE
        new_chart.set("visible_to_roles", [])
        new_chart.insert()
        return new_chart.name


def import_chart(chart, workbook):
    """Copy an exported chart into `workbook`, with the query it is built on.

    The query goes in first, so the chart is inserted already pointing at the
    copy. `validate` reads the link, and a link to the exporting site's query is
    a state it would read as the real one.
    """
    from insights.insights.doctype.insights_query_v3.insights_query_v3 import already_in_workbook

    chart = frappe.parse_json(chart)
    chart = deep_convert_dict_to_dict(chart)

    new_chart = frappe.new_doc("Insights Chart v3")
    new_chart.update(chart.doc)
    new_chart.workbook = workbook

    exported = (chart.get("dependencies") or {}).get("queries") or {}
    if chart.doc.query in exported and not already_in_workbook(chart.doc.query, workbook):
        new_chart.query = import_query(exported[chart.doc.query], workbook)

    if not hasattr(new_chart, "sort_order") or new_chart.sort_order is None:
        max_sort_order = (
            frappe.db.get_value(
                "Insights Chart v3",
                filters={"workbook": workbook},
                fieldname="max(sort_order)",
            )
            or -1
        )
        new_chart.sort_order = max_sort_order + 1
    new_chart.insert()

    return new_chart.name
