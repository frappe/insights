# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What an authoring surface is allowed to ask for.

The builder draws a chart that is not saved yet, so it cannot name one. It sends
the shape it is editing — chart type, source query and config — and gets back
the rows a saved chart with that shape would give. `insights.api.viewer` is the
same answer for a chart that has a name; the deriver behind both is the one in
`chart_query`.

What makes this a separate door is the rest of the answer: the operations the
server derived, and the SQL they ran as. A viewer response carries neither, and
that is the whole reason the reading surfaces are safe to open to a guest. Here
they are the point — the builder shows the SQL it ran, and lifts a drill level
into the query builder — so this door is closed to anyone without an authoring
seat.

Two things are checked: `check_app_permission`, which is the seat, and read on
the source query, because naming a query is how this endpoint says what to run.
There is no document to check write on — the whole point of these endpoints is
that nothing has been saved yet — so those two are the whole of the gate.

That gate is deliberately looser than the viewer door's, and it can afford to
be. A viewer's drill is bounded to the chart's own surface because the wire must
not widen what a published chart exposes. Here the caller already holds the seat
that lets them build any query they like, so a pipeline they send is a pipeline
they could have run anyway; the engine applies their permissions to it either
way.
"""

import frappe
from frappe import _

from insights.decorators import validate_type
from insights.insights.doctype.insights_chart_v3.chart_drill import drill_data, drill_dimensions
from insights.insights.doctype.insights_chart_v3.chart_query import (
    column_granularity,
    config_errors,
)
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import route_filters
from insights.permissions import check_app_permission

CHART = "Insights Chart v3"
QUERY = "Insights Query v3"


@frappe.whitelist()
@validate_type
def get_chart_data(
    chart_type: str,
    query: str,
    config: dict | None = None,
    chart_name: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
    page: int = 1,
    page_size: int | None = None,
    force: bool = False,
):
    """The rows this config produces, and the operations that produced them.

    A half-configured chart is the builder's normal state, not a failure: the
    config errors come back in the response so the card can say what is missing
    and keep the last picture on screen. A saved chart throws instead — nobody
    is editing it, so an unfilled slot there is a chart that cannot be drawn.

    A card on the builder's dashboard grid also sends `dashboard_items`, the
    filter `filters` state and the `chart_name` those items link by. Routing
    them is `route_filters`' job, the same one `insights.api.viewer` calls — the
    builder is editing items it has not saved, and that is the only reason it
    sends them rather than naming a dashboard. It does not widen this door: what
    comes back are filters keyed by the queries the links name, and a query the
    chart does not read matches nothing in its graph. The endpoint used to take
    the routed dict straight from the client, so the client now says strictly
    less than it did.
    """
    check_authoring_seat(query)

    adhoc_filters = route_filters(dashboard_items, chart_name, filters) if chart_name else None

    errors = config_errors(chart_type, query, config)
    if errors:
        return {"errors": errors}

    chart = preview_chart(chart_type, query, config)

    operations = chart.get_operations()
    chart_query = chart.get_query()
    result = chart_query.execute(
        force=force,
        page=page,
        page_size=page_size or (config or {}).get("limit") or 100,
        adhoc_filters=adhoc_filters,
    )

    return {
        "errors": [],
        "columns": result["columns"],
        "rows": result["rows"],
        "granularity": column_granularity(operations),
        # the same field the viewer response carries, so a card reads its drill
        # candidates off whichever feed drew it
        "drill": {"dimensions": drill_dimensions(chart, operations)},
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
        # the authoring half of the answer
        "operations": operations,
        "sql": result["sql"],
        # a drill level opened in the query builder has to run against the same
        # connection the chart did
        "use_live_connection": bool(chart_query.use_live_connection),
        # what the grid's filters routed to. The author may already read the SQL
        # these ran as, so this says nothing new to them
        "adhoc_filters": adhoc_filters,
    }


@frappe.whitelist()
@validate_type
def get_drill_data(
    query: str,
    drill_stack: list,
    chart_type: str | None = None,
    config: dict | None = None,
    operations: list | None = None,
    chart_name: str | None = None,
    dashboard_items: list | None = None,
    filters: dict | None = None,
):
    """What is behind a segment, for a shape that has not been saved.

    The walk is `insights.api.viewer.get_drill_data`'s walk, level for level —
    the same `drill_stack` of plain values, answered by the same drill layer.
    What differs is how the caller says what it is drilling. A saved chart is a
    name; here it is either the config the builder is editing, or, for the query
    builder's own result table, the `operations` it is editing. Neither exists
    as a document yet, which is the whole reason this door exists.

    The answer carries the sliced pipeline, because "open as query" hands the
    level to the full builder. That field is exactly what the viewer door must
    never return — see this module's docstring.
    """
    check_authoring_seat(query)

    chart = preview_chart(chart_type, query, config)
    adhoc_filters = route_filters(dashboard_items, chart_name, filters) if chart_name else None

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


@frappe.whitelist()
@validate_type
def get_drill_dimensions(
    query: str,
    chart_type: str | None = None,
    config: dict | None = None,
    operations: list | None = None,
):
    """What a segment of this shape can be broken down by.

    A chart's candidates ride its data response, on both doors. A query builder
    fetches its rows through the query document itself, so it has no such
    response to ride — hence this. Same answer, asked for on its own.
    """
    check_authoring_seat(query)

    chart = preview_chart(chart_type, query, config)
    return {"dimensions": drill_dimensions(chart, operations)}


def check_authoring_seat(query: str):
    if not check_app_permission():
        frappe.throw(_("You do not have permission to access this resource"), frappe.PermissionError)

    frappe.has_permission(QUERY, ptype="read", doc=query, throw=True)


def preview_chart(chart_type: str | None, query: str, config: dict | None):
    """A chart document for a shape nobody has saved, made to run and thrown away.

    The query builder sends no chart at all — it names its source query and
    hands over its own operations — and this is still what carries them: the
    connection, the execution reference and the authority all hang off the
    source query either way.
    """
    chart = frappe.new_doc(CHART)
    # the throwaway query this becomes is named after the chart, and the builder
    # names its source query in the same breath — two documents in one build, so
    # this one needs a name of its own or the cycle guard mistakes it for the other
    chart.name = f"preview-of-{query}"
    chart.chart_type = chart_type
    chart.query = query
    chart.config = frappe.as_json(config or {})
    return chart
