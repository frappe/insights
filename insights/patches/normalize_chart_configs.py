import frappe

from insights.insights.doctype.insights_chart_v3.chart_query import normalize_chart_config

CHART = "Insights Chart v3"


def execute():
    """Every stored chart config in the shape the readers read, written once.

    Runs `normalize_chart_config` over every stored config. See its docstring
    for why.

    Idempotent: a chart already in the shape is not written.
    """
    for chart in frappe.get_all(CHART, fields=["name", "config", "chart_type"]):
        config = frappe.parse_json(chart.config)
        if not isinstance(config, dict):
            continue

        written = normalize_chart_config(config, chart.chart_type)
        if written == config:
            continue

        # Nothing on the chart is derived from its config, so this keeps
        # `modified` where the author left it.
        frappe.db.set_value(CHART, chart.name, "config", frappe.as_json(written), update_modified=False)
