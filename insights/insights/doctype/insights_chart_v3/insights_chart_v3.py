# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from insights.insights.doctype.insights_chart_v3.chart_query import (
    comparison_sources,
    comparison_timespans,
    config_errors,
    derive_operations,
    period_column,
    sparkline_operations,
)
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import route_filters
from insights.insights.doctype.insights_query_v3.insights_query_v3 import import_query
from insights.insights.query_builders.sql_functions import resolve_timespan
from insights.utils import deep_convert_dict_to_dict

QUERY = "Insights Query v3"

# A page of an ascending series ends at its oldest rows, so a series cut by the
# card's own page size would stop short of the number it is drawn under. This is
# the bound instead: more periods than any window a card is read over.
SPARKLINE_MAX_POINTS = 1000


class InsightsChartv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        chart_type: DF.Data | None
        config: DF.JSON | None
        folder: DF.Data | None
        is_public: DF.Check
        old_name: DF.Data | None
        permission_user: DF.Link | None
        query: DF.Link | None
        sort_order: DF.Int
        title: DF.Data | None
        workbook: DF.Link
    # end: auto-generated types

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.config, dict):
            self.config = frappe.as_json(self.config)
        return super().get_valid_dict(*args, **kwargs)

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)
        d.read_only = not self.has_permission("write")
        return d

    def validate(self):
        from insights.permissions import check_chart_query_access

        check_chart_query_access(self)

    @frappe.whitelist()
    def update_access(self, is_public: bool):
        """Publish this chart, or withdraw it.

        Publishing is a grant of the publisher's own read access to everyone
        with the link, so it is the `share` permission and not `write`. The
        publisher is recorded here because the public execution has no caller of
        its own to filter rows by. `is_public` and `permission_user` are both
        permlevel 1, so this method is the only way in.

        The `query` link needs no check here. This writes neither link nor
        content, and a caller who reached this method can read the chart, which
        `_build_query_permission_query` already turns into read on its query.
        """
        if not frappe.has_permission("Insights Chart v3", ptype="share", doc=self.name):
            frappe.throw(frappe._("You do not have permission to share this chart"), frappe.PermissionError)

        is_public = bool(frappe.parse_json(is_public))
        self.db_set(
            {
                "is_public": int(is_public),
                "permission_user": frappe.session.user if is_public else None,
            }
        )

    def on_trash(self):
        # Clean up empty folders
        if self.folder:
            self.cleanup_empty_folder(self.folder)

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

    @frappe.whitelist()
    def get_data(
        self,
        force: bool = False,
        page: int = 1,
        page_size: int = 100,
        chart_name: str | None = None,
        dashboard_items: list | None = None,
        filters: dict | None = None,
    ):
        """Fetch this chart's rows, for a surface that reads the saved chart.

        A request may name a chart but must not describe one: `run_doc_method`
        builds `self` out of the request payload, so the stored chart is re-read
        here and it alone decides the query that runs.

        Dashboard filter state arrives unrouted — the grid's `dashboard_items`,
        the `filters` state and the `chart_name` the links name — and
        `route_filters` decides which query each filter lands on, the same way
        it does for the builder's own feed in `insights.api.authoring`.

        A windowed card's sparkline rides along under `sparkline`. It runs here
        and not through a call of its own so that a client never has to know
        which cards need a second fetch, and so that a filter cannot reach one
        execution and miss the other.
        """
        chart = frappe.get_doc(self.doctype, self.name)
        adhoc_filters = route_filters(dashboard_items, chart_name, filters) if chart_name else None

        query = chart.get_query()
        result = query.execute(
            force=force,
            page=page,
            page_size=page_size,
            adhoc_filters=adhoc_filters,
        )
        sparkline = chart.get_sparkline_data(force=force, adhoc_filters=adhoc_filters)

        if sparkline:
            result["sparkline"] = sparkline
        if rows := chart.comparison_rows(result["rows"]):
            result["comparison_rows"] = rows
        return result

    def comparison_rows(self, rows: list[dict]) -> dict[str, int | None]:
        """Which row answers each comparison, keyed by the source that asks it.

        A reading is measured against a row of its own, so two readings asking
        different questions read different rows. Counting back from the end
        cannot say which is which: a card fetches one stretch per distinct
        comparison, they come back oldest first, and a stretch with no data
        comes back not at all.

        Answered here because the answer is a date. A span carries none until
        the query runs, and the same span resolved a second time in the browser
        would be resolved against a different clock and a different fiscal
        calendar.

        A grain period fetches nothing beside itself — every period it has is
        already a row — so the period before this one is the row before the
        last, and that is the whole of what it can answer.

        A source the card asked and got no row for is named with `None`: the
        question stands and the card prints it with no figure. A source that is
        missing is one this period cannot be asked at all.
        """
        if self.chart_type != "Number" or not rows:
            return {}

        config = frappe.parse_json(self.config or "{}")
        timespans = comparison_timespans(self.chart_type, config)
        if not timespans:
            if "previous" not in comparison_sources(self.chart_type, config):
                return {}
            return {"previous": len(rows) - 2 if len(rows) > 1 else None}

        column = period_column(self.chart_type, config)
        starts = {getdate(row[column]): index for index, row in enumerate(rows) if row.get(column)}

        return {source: starts.get(resolve_timespan(timespan)[0]) for source, timespan in timespans.items()}

    def get_sparkline_data(self, force: bool = False, adhoc_filters: dict | None = None):
        """The series behind this card's sparkline, or nothing when it draws none.

        Only a card that asks for both a sparkline and a window runs it. Execution
        is limited rather than queued — a dashboard already pushes the pool — so a
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

    def get_query(self, operations: list | None = None):
        """A query document for this chart's operations, made to run and thrown away.

        Nothing about it is worth keeping: the operations follow from the config, so
        the config is the only copy. It is never inserted, and it names the source
        query as its execution reference so a chart run still counts as usage of the
        tables it read.

        `operations` runs something built out of the chart's own instead — a drill's
        sliced pipeline — against the same source and connection the chart uses.
        """
        query = frappe.new_doc(QUERY)
        query.name = self.name
        query.title = self.title
        query.workbook = self.workbook
        query.operations = frappe.as_json(self.get_operations() if operations is None else operations)
        query.use_live_connection = frappe.db.get_value(QUERY, self.query, "use_live_connection")
        query.flags.execution_reference = self.query
        return query

    def get_operations(self):
        """The operations that produce the chart's rows.

        The source query, the chart's own filters, its summarize or pivot, and its
        sort — derived here from the config every time the chart runs. This used to
        be read off a second query document the browser filled in, and a chart no
        browser had visited fell back to drawing its source query: a whole shipped
        workbook rendered raw tables, every number wrong and nothing said so. A config
        that cannot be drawn is an error, not a row set.
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
        new_chart = frappe.copy_doc(self)
        new_chart.title = f"{self.title} (Copy)"
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
