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
they are the point — the builder shows the SQL it ran, and forks the operations
into a drill-down — so this door is closed to anyone without an authoring seat.

Two things are checked: `check_app_permission`, which is the seat, and read on
the source query, because naming a query is how this endpoint says what to run.
"""

import frappe
from frappe import _

from insights.decorators import validate_type
from insights.insights.doctype.insights_chart_v3.chart_query import (
    column_granularity,
    config_errors,
)
from insights.permissions import check_app_permission

CHART = "Insights Chart v3"
QUERY = "Insights Query v3"


@frappe.whitelist()
@validate_type
def get_chart_data(
    chart_type: str,
    query: str,
    config: dict | None = None,
    adhoc_filters: dict | None = None,
    page: int = 1,
    page_size: int | None = None,
    force: bool = False,
):
    """The rows this config produces, and the operations that produced them.

    A half-configured chart is the builder's normal state, not a failure: the
    config errors come back in the response so the card can say what is missing
    and keep the last picture on screen. A saved chart throws instead — nobody
    is editing it, so an unfilled slot there is a chart that cannot be drawn.
    """
    if not check_app_permission():
        frappe.throw(_("You do not have permission to access this resource"), frappe.PermissionError)

    frappe.has_permission(QUERY, ptype="read", doc=query, throw=True)

    errors = config_errors(chart_type, query, config)
    if errors:
        return {"errors": errors}

    chart = frappe.new_doc(CHART)
    # the throwaway query this becomes is named after the chart, and the builder
    # names its source query in the same breath — two documents in one build, so
    # this one needs a name of its own or the cycle guard mistakes it for the other
    chart.name = f"preview-of-{query}"
    chart.chart_type = chart_type
    chart.query = query
    chart.config = frappe.as_json(config or {})

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
        "time_taken": result["time_taken"],
        "executed_at": frappe.utils.now(),
        # the authoring half of the answer
        "operations": operations,
        "sql": result["sql"],
        # a drill-down forks the operations above, and has to run against the
        # same connection the chart did
        "use_live_connection": bool(chart_query.use_live_connection),
    }
