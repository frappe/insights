# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What an authoring surface may ask for.

The builder draws a chart that is not saved yet, so it cannot name one. It sends
the shape it is editing (chart type, source query and config) and gets back the
rows a saved chart with that shape would give. A saved chart's own `get_data`
gives the same answer for a chart that has a name. One deriver, `chart_query`,
serves both.

What makes this a separate endpoint is the rest of the answer: the operations
the server derived, and the SQL they ran as. A saved chart's response carries
neither, which is why a public link is safe to open to a guest. Here they are
the point. The builder shows the SQL it ran and lifts a drill level into the
query builder, so this endpoint is closed to anyone without an authoring seat.

Two things are checked: the `Insights User` role `insights_whitelist` requires,
which is the seat, and read on the source query, because naming a query is how
this endpoint says what to run. Nothing has been saved yet, so there is no
document to check write on, and those two are the whole gate.

The caller already holds the seat that lets them build any query, so a pipeline
they send is one they could have run anyway. The engine applies their
permissions to it either way.
"""

import frappe

from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_chart_v3.chart_drill import drill_data, drill_dimensions
from insights.insights.doctype.insights_chart_v3.chart_query import (
    column_granularity,
    config_errors,
)
from insights.insights.doctype.insights_chart_v3.record_link import record_links
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import (
    route_card_filters,
    route_filters,
)

CHART = "Insights Chart v3"
QUERY = "Insights Query v3"


@insights_whitelist()
def get_chart_data(
    chart_type: str,
    query: str,
    config: dict | None = None,
    chart_name: str | None = None,
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
    and keep the last picture on screen. A saved chart throws instead. Nobody is
    editing it, so an unfilled slot there is a chart that cannot be drawn.

    A card on the builder's dashboard grid also sends `dashboard_items`, the
    `filters` state and the `chart_name` those items link by. Routing them is
    `route_filters`' job, the same one a saved chart's `get_data` calls. The
    builder is editing items it has not saved, which is the only reason it sends
    them rather than naming a dashboard. It does not widen this endpoint: what
    comes back are filters keyed by the queries the links name, and a query the
    chart does not read matches nothing in its graph.

    `card_filters` is the reader's own filter on one card. It names a column the
    card draws and lands on the card's own derived query.
    """
    check_read_access(query, chart_name)

    adhoc_filters = route_filters(dashboard_items, chart_name, filters) if chart_name else None
    adhoc_filters = route_card_filters(chart_name, card_filters, adhoc_filters) if chart_name else None

    errors = config_errors(chart_type, query, config)
    if errors:
        return {"errors": errors}

    chart = preview_chart(chart_type, query, config, name=chart_name)

    operations = chart.get_operations()
    chart_query = chart.get_query()
    result = chart_query.execute(
        force=force,
        page=page,
        page_size=page_size or (config or {}).get("limit") or 100,
        adhoc_filters=adhoc_filters,
    )
    result["rows"] = chart.periods_oldest_last(result["rows"])
    # a span card's series is fetched here too, under the same filters as the
    # rows, so the builder draws the card a reader will see
    sparkline = chart.get_sparkline_data(force=force, adhoc_filters=adhoc_filters)

    return {
        "errors": [],
        "columns": result["columns"],
        "rows": result["rows"],
        "granularity": column_granularity(operations),
        # so the builder's card draws the same links a reader will see
        **({"record_links": links} if (links := record_links(operations, result["columns"])) else {}),
        **({"sparkline": sparkline} if sparkline else {}),
        # so the card reads the span it asked for rather than counting back from
        # the end
        **({"comparison_rows": rows} if (rows := chart.comparison_rows(result["rows"])) else {}),
        "drill": {"dimensions": drill_dimensions(chart, operations)},
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
        "operations": operations,
        "sql": result["sql"],
        # a drill level opened in the query builder has to run against the same
        # connection the chart did
        "use_live_connection": bool(chart_query.use_live_connection),
        # the author may already read the SQL these ran as, so returning them
        # says nothing new
        "adhoc_filters": adhoc_filters,
    }


@insights_whitelist()
def get_drill_data(
    query: str,
    drill_stack: list,
    chart_type: str | None = None,
    config: dict | None = None,
    operations: list | None = None,
    chart_name: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    card_filters: list | None = None,
):
    """What is behind a segment, for a shape that has not been saved.

    The walk is `chart_drill`'s, level for level: a `drill_stack` of plain
    values, answered by the drill layer. The caller says what it is drilling:
    the config the builder is editing, or, for the query builder's own result
    table, the `operations` it is editing. Neither exists as a document yet,
    which is why this endpoint exists.

    The answer carries the cut pipeline, because "open as query" hands the
    level to the full builder. That field is what a reading surface must never
    receive (see the module docstring). A rows level here answers with that
    pipeline and its columns and no rows: the caller runs it itself.
    """
    check_read_access(query, chart_name)

    chart = preview_chart(chart_type, query, config, name=chart_name)
    adhoc_filters = route_filters(dashboard_items, chart_name, filters) if chart_name else None
    adhoc_filters = route_card_filters(chart_name, card_filters, adhoc_filters) if chart_name else None

    response = drill_data(
        chart,
        drill_stack,
        adhoc_filters=adhoc_filters,
        operations=operations,
        with_operations=True,
    )
    # the query the level opens as runs where the chart ran
    response["use_live_connection"] = bool(frappe.db.get_value(QUERY, query, "use_live_connection"))
    return response


@insights_whitelist()
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
    """Read on every document this request names. The seat is the decorator's."""
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


def preview_chart(chart_type: str | None, query: str, config: dict | None, name: str | None = None):
    """A chart document for a shape nobody has saved, made to run and thrown away.

    The query builder sends no chart at all, only its source query and its own
    operations, and this still carries them: the connection, the execution
    reference and the authority all come from the source query either way.

    `name` is the chart the caller is drawing, when it is drawing one. The
    throwaway query takes that name, so a filter linked to the chart lands on it
    here as it does on the saved chart's own read path.
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
