# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What the Builder may ask for.

The builder renders a chart that is not saved yet, so it cannot name one. It sends
the shape it is editing (chart type, source query and config) and gets back the
rows a saved chart with that shape would give. `InsightsChartv3.fetch` gives
the same answer for a chart that has a name. One deriver, `chart_query`, serves
both.

What makes this a separate endpoint is the rest of the answer: the operations
the server derived, and the SQL they ran as. A saved chart's response includes
neither, which is why a public link is safe to open to a guest. Here they are
the point. The builder shows the SQL it ran and opens a drill level as a query
of its own, so this endpoint is closed to anyone without an Insights role.

Two things are checked: the `Insights User` role `insights_whitelist` requires,
and read on the source query, because naming a query is how this endpoint says
what to run. A caller who names a saved chart they may not write is not its
writer (`is_writer`). `insights.api.view` answers them, as it answers every
reader of the chart.

The caller already holds the role that lets them build any query, so a pipeline
they send is one they could have run anyway.

The named chart, not the caller, decides whose permissions the engine applies.
This module enters `permission_user.runs_as` exactly as `insights.api.view`
does, so the Builder and a reader's card always agree about one chart.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from insights import user_permissions
from insights.api import view
from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_chart_v3.chart_drill import (
    asks_for_rows,
    drill_data,
    drill_dimensions,
    drill_rows_export,
    drill_rows_range,
    drill_rows_values,
)
from insights.insights.doctype.insights_chart_v3.chart_query import (
    column_granularity,
    config_errors,
)
from insights.insights.doctype.insights_chart_v3.record_link import record_links
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
    can_filter_card,
    route_card_filters,
    route_filters,
    routed_filter_links,
)
from insights.insights.query_builders.sql_functions import reading_day
from insights.not_permitted import answers_refusal
from insights.permission_user import runs_as
from insights.permissions import can_export, can_read_rows, can_write

CHART = "Insights Chart v3"
QUERY = "Insights Query v3"


@insights_whitelist()
@answers_refusal(lambda: {"errors": [], "columns": [], "rows": [], "executed_at": frappe.utils.now()})
def get_chart_data(
    chart_type: str,
    query: str,
    config: dict | None = None,
    chart_name: str | None = None,
    dashboard: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    page: int = 1,
    page_size: int | None = None,
    force: bool = False,
):
    """The rows this config produces, and the operations that produced them.

    A half-configured chart is the builder's normal state, not a failure: the
    config errors come back in the response so the card can say what is missing
    and keep the last chart on screen.

    A card on the builder's dashboard grid also sends `dashboard_items`, the
    `filters` state and the `chart_name` those items link by. Routing them is
    `route_filters`' job, the same one `insights.api.view` calls for a saved
    dashboard. The builder is editing items it has not saved, which is the only
    reason it sends them rather than naming a dashboard. It does not widen this
    endpoint: what comes back are filters keyed by the queries the links name,
    and a query the chart does not read matches nothing in its graph.

    `card_filters` is the reader's own filter on one card. It names a column the
    card shows and lands on the card's own derived query.

    A caller who may not write the saved chart they name is its reader, and
    gets the reader's answer. It is routed by the saved `dashboard`, never by
    the `dashboard_items` in the request.
    """
    if not is_writer(chart_name):
        return view.get_chart_data(
            chart=chart_name,
            dashboard=dashboard,
            filters=filters,
            card_filters=card_filters,
            force=force,
            page=page,
        )

    chart, adhoc_filters = drilled_shape(
        query, chart_type, config, chart_name, dashboard_items, filters, card_filters
    )
    chart_type, config = chart.chart_type, frappe.parse_json(chart.config)

    errors = config_errors(chart_type, chart.query, config)
    if errors:
        return {"errors": errors}

    operations = chart.get_operations()
    chart_query = chart.get_query()
    read_on = str(getdate(reading_day()))
    # read before the rows, as `view.chart_answer` does
    modified = chart.last_modified()
    with runs_as(chart):
        result = chart_query.execute(
            force=force,
            page=page,
            page_size=page_size or (config or {}).get("limit") or 100,
            adhoc_filters=adhoc_filters,
        )
        # read before the sparkline runs, because its build clears this record
        scope = user_permissions.scope(frappe.session.user)
        # a span card's series is fetched here too, under the same filters as the
        # rows, so the builder renders the card a reader will see
        sparkline = chart.get_sparkline_data(force=force, adhoc_filters=adhoc_filters)
    result["rows"] = chart.periods_oldest_last(result["rows"])

    return {
        "errors": [],
        "columns": result["columns"],
        "rows": result["rows"],
        "granularity": column_granularity(operations),
        # so the builder's card shows the same links a reader will see
        **({"record_links": links} if (links := record_links(operations, result["columns"])) else {}),
        **({"sparkline": sparkline} if sparkline else {}),
        # so the card reads the span it asked for rather than counting back from
        # the end
        **({"comparison_rows": rows} if (rows := chart.comparison_rows(result["rows"])) else {}),
        # which permissions narrowed these rows, in the same shape as the
        # reader's card
        **scope,
        "drill": {"dimensions": drill_dimensions(chart, operations)},
        "can_filter": can_filter_card(chart.name),
        "can_read_rows": can_read_rows(chart),
        "can_export": can_export(chart),
        # the symbol of every currency code in these rows, as a reader's card
        # gets. A Builder grid card may be the first thing this session ran, so
        # the query editor may not have filled the client's map yet
        "currency_symbols": result["currency_symbols"],
        # the date this card's Spans resolved against, so a drill uses the same
        # date as the number
        "read_on": read_on,
        # the version of the saved chart this ran as. A drill sends it back and
        # is refused once another user's save changed it
        "modified": modified,
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
        "operations": operations,
        "sql": result["sql"],
        # a drill level opened in the query builder has to run against the same
        # connection the chart did
        "use_live_connection": bool(chart_query.use_live_connection),
    }


@insights_whitelist()
def get_chart_count(
    chart_type: str,
    query: str,
    config: dict | None = None,
    chart_name: str | None = None,
    dashboard: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    force: bool = False,
):
    """The total number of rows behind the pages of `get_chart_data`, under the same filters.

    A caller who is not the author counts the saved chart through `insights.api.view`.
    """
    if not is_writer(chart_name):
        return view.get_chart_count(
            chart=chart_name, dashboard=dashboard, filters=filters, card_filters=card_filters, force=force
        )

    chart, adhoc_filters = drilled_shape(
        query, chart_type, config, chart_name, dashboard_items, filters, card_filters
    )
    if config_errors(chart.chart_type, chart.query, frappe.parse_json(chart.config)):
        return 0
    return chart.count_rows(adhoc_filters, force=force)


@insights_whitelist()
def download_chart_rows(
    chart_type: str,
    query: str,
    config: dict | None = None,
    chart_name: str | None = None,
    dashboard: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    format: str = "csv",
):
    """Every row behind the pages of `get_chart_data` as a file, under the same filters.

    A caller who is not the author downloads the saved chart through `insights.api.view`.
    """
    if not is_writer(chart_name):
        return view.download_chart_rows(
            chart=chart_name, dashboard=dashboard, filters=filters, card_filters=card_filters, format=format
        )

    chart, adhoc_filters = drilled_shape(
        query, chart_type, config, chart_name, dashboard_items, filters, card_filters
    )
    return chart.export_rows(format, adhoc_filters)


@insights_whitelist()
@answers_refusal(lambda: {"columns": [], "rows": []})
def get_drill_data(
    query: str,
    drill_stack: list,
    chart_type: str | None = None,
    config: dict | None = None,
    operations: list | None = None,
    chart_name: str | None = None,
    dashboard: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    sort: list | None = None,
    find: str | None = None,
    page: int = 1,
    row_filters: list | None = None,
):
    """What is behind a segment, for a shape that has not been saved.

    The walk is `chart_drill`'s, level for level: a `drill_stack` of plain
    values, answered by the drill layer. The caller says what it is drilling:
    the config the builder is editing, or, for the query builder's own result
    table, the `operations` it is editing. Neither exists as a document yet,
    which is why this endpoint exists.

    A rows level is read here as `insights.api.view` reads one, with the
    reader's `sort`, `find`, `page` and `row_filters`. The answer also includes
    the cut pipeline, because "open as query" adds the level to the workbook as
    a new query. A View must never receive that field (see the module
    docstring).

    A refusal is a normal answer, for the reason `view.get_drill_data` gives:
    the dialog renders a refused level, and the Builder uses the same dialog
    component as a View.

    A caller who is not the author of the chart they name drills it as a
    reader, through `insights.api.view`.
    """
    if not is_writer(chart_name):
        return view.get_drill_data(
            chart=chart_name,
            dashboard=dashboard,
            filters=filters,
            drill_stack=drill_stack,
            sort=sort,
            find=find,
            page=page,
            row_filters=row_filters,
        )

    chart, adhoc_filters = drilled_shape(
        query, chart_type, config, chart_name, dashboard_items, filters, card_filters
    )

    # `drill_data` enters `runs_as` and `read_on` itself, for the chart it is given
    response = drill_data(
        chart,
        drill_stack,
        adhoc_filters=adhoc_filters,
        operations=operations,
        with_operations=True,
        sort=sort,
        find=find,
        page=page,
        row_filters=row_filters,
    )
    if asks_for_rows(drill_stack):
        response["can_export"] = can_export(chart)
    # dashboard filters linked to a query that the chart's query reads narrowed
    # these rows. The query the level opens as has no step to hold them
    # (`_as_opened` keeps only the filters on the chart's own query)
    response["unapplied_filters"] = [
        name
        for name, linked, _column, _state in routed_filter_links(dashboard_items, chart_name, filters)
        if linked != chart.query
    ]
    # the query the level opens as runs where the chart ran
    response["use_live_connection"] = bool(frappe.db.get_value(QUERY, query, "use_live_connection"))
    return response


@insights_whitelist()
def download_drill_rows(
    query: str,
    drill_stack: list,
    chart_type: str | None = None,
    config: dict | None = None,
    operations: list | None = None,
    chart_name: str | None = None,
    dashboard: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    sort: list | None = None,
    find: str | None = None,
    format: str = "csv",
    row_filters: list | None = None,
):
    """The rows behind a segment of an unsaved shape as a file, read as `get_drill_data` reads them."""
    if not is_writer(chart_name):
        return view.download_drill_rows(
            chart=chart_name,
            dashboard=dashboard,
            filters=filters,
            drill_stack=drill_stack,
            sort=sort,
            find=find,
            format=format,
            row_filters=row_filters,
        )

    chart, adhoc_filters = drilled_shape(
        query, chart_type, config, chart_name, dashboard_items, filters, card_filters
    )
    if not can_export(chart):
        frappe.throw(_("You are not allowed to download data"), exc=frappe.PermissionError)

    return drill_rows_export(
        chart,
        drill_stack,
        adhoc_filters=adhoc_filters,
        sort=sort,
        find=find,
        format=format,
        row_filters=row_filters,
        operations=operations,
    )


@insights_whitelist()
@answers_refusal(list)
def get_drill_rows_values(
    query: str,
    drill_stack: list,
    column: str,
    chart_type: str | None = None,
    config: dict | None = None,
    operations: list | None = None,
    chart_name: str | None = None,
    dashboard: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    row_filters: list | None = None,
    search_term: str | None = None,
):
    """The values listed by the reader's own filter on a rows level of an unsaved shape."""
    if not is_writer(chart_name):
        return view.get_drill_rows_values(
            chart=chart_name,
            column=column,
            drill_stack=drill_stack,
            dashboard=dashboard,
            filters=filters,
            row_filters=row_filters,
            search_term=search_term,
        )

    chart, adhoc_filters = drilled_shape(
        query, chart_type, config, chart_name, dashboard_items, filters, card_filters
    )
    return drill_rows_values(
        chart,
        drill_stack,
        column,
        search_term=search_term,
        adhoc_filters=adhoc_filters,
        row_filters=row_filters,
        operations=operations,
    )


@insights_whitelist()
@answers_refusal(lambda: None)
def get_drill_rows_range(
    query: str,
    drill_stack: list,
    column: str,
    chart_type: str | None = None,
    config: dict | None = None,
    operations: list | None = None,
    chart_name: str | None = None,
    dashboard: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
    row_filters: list | None = None,
):
    """The range shown by a number filter on a rows level of an unsaved shape."""
    if not is_writer(chart_name):
        return view.get_drill_rows_range(
            chart=chart_name,
            column=column,
            drill_stack=drill_stack,
            dashboard=dashboard,
            filters=filters,
            row_filters=row_filters,
        )

    chart, adhoc_filters = drilled_shape(
        query, chart_type, config, chart_name, dashboard_items, filters, card_filters
    )
    return drill_rows_range(
        chart,
        drill_stack,
        column,
        adhoc_filters=adhoc_filters,
        row_filters=row_filters,
        operations=operations,
    )


def drilled_shape(query, chart_type, config, chart_name, dashboard_items, filters, card_filters):
    """The chart this request runs, and what narrows it."""
    check_read_access(query, chart_name)

    chart = chart_to_run(chart_type, query, config, chart_name)
    adhoc_filters = route_filters(dashboard_items, chart_name, filters) if chart_name else None
    adhoc_filters = route_card_filters(chart.name, card_filters, adhoc_filters) if chart_name else None
    return chart, adhoc_filters


@insights_whitelist()
@answers_refusal(lambda: {"dimensions": []})
def get_drill_dimensions(
    query: str,
    chart_type: str | None = None,
    config: dict | None = None,
    operations: list | None = None,
):
    """What a segment of this shape can be broken down by.

    A chart's candidates come back with its data response. A query builder
    fetches its rows through the query document, so it has no such response and
    asks for the same answer here.
    """
    check_read_access(query)

    chart = preview_chart(chart_type, query, config)
    return {"dimensions": drill_dimensions(chart, operations)}


def check_read_access(query: str, chart_name: str | None = None):
    """Read on every document this request names. `insights_whitelist` checks the role."""
    frappe.has_permission(QUERY, ptype="read", doc=query, throw=True)

    # the preview runs under the named chart, and that name tells the engine
    # which other queries this execution is already authorized for. A document
    # the caller cannot read must not be that name: a chart, because the engine
    # reads its stored query, and a query, because the engine reads that query's
    # own dependencies under the same name. A name no document holds is the
    # builder's unsaved card, which authorizes nothing.
    for doctype in (CHART, QUERY):
        if chart_name and frappe.db.exists(doctype, chart_name):
            frappe.has_permission(doctype, ptype="read", doc=chart_name, throw=True)


def is_writer(chart_name: str | None) -> bool:
    """Whether the caller is the writer of what runs under `chart_name`.

    Naming a saved chart runs the request under that chart's Run as owner
    setting (`permission_user_for`). A shape the caller sent may use it only if
    the caller may change the chart, the same answer as the form's
    `read_only`, because saving that shape would make it the chart's content.
    Anyone else is a reader of the chart, whatever they sent. A name no chart
    has is the Builder's unsaved card, which has no such setting.
    """
    if not chart_name or not frappe.db.exists(CHART, chart_name):
        return True

    return can_write(frappe.get_doc(CHART, chart_name))


def chart_to_run(chart_type: str | None, query: str, config: dict | None, chart_name: str | None):
    """The shape in the request, run under the saved chart it names, if any."""
    saved = chart_name and frappe.db.exists(CHART, chart_name)
    return preview_chart(chart_type, query, config, name=chart_name if saved else None)


def preview_chart(chart_type: str | None, query: str, config: dict | None, name: str | None = None):
    """A chart document for a shape nobody has saved, made to run and thrown away.

    The query builder sends no chart at all, only its source query and its own
    operations, and this still passes them: the connection and the execution
    reference come from the source query either way.

    `name` is the saved chart this preview runs as, when `chart_to_run` found
    one. The throwaway query takes that name, so a filter linked to the chart
    applies here as it does on the saved chart's own read path. A preview with
    no saved chart is named after its source query instead. Card filters are
    routed to `chart.name` in both cases.
    """
    chart = frappe.new_doc(CHART)
    # the throwaway query this becomes is named after the chart, and the builder
    # names its source query in the same request. Two documents in one build, so
    # this one needs a name of its own or the cycle guard mistakes it for the other
    chart.name = name or f"preview-of-{query}"
    chart.chart_type = chart_type
    chart.query = query
    chart.config = frappe.as_json(config or {})
    return chart
