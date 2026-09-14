import frappe

from insights.insights.doctype.insights_chart_v3.chart_query import normalize_number_shapes

CHART = "Insights Chart v3"


def execute():
    """What a number card reads and what it measures the reading against, written
    once in the shape the reader reads.

    Three releases have written what a reading is measured against: a `target`
    and a `comparison` beside the reading, the `references` list before it, and
    a chart-level `comparison` flag before that, which said one previous-period
    comparison for every reading. Two have written the period the card reads: the
    chart's own `window`, and a granularity on the date column before it. Every
    chart is rewritten into the first of each, so nothing reads the older shapes.

    Idempotent — a chart already in the shape is left alone.
    """
    for chart in frappe.get_all(CHART, filters={"chart_type": "Number"}, fields=["name", "config"]):
        config = frappe.parse_json(chart.config)
        if not isinstance(config, dict):
            continue
        if not normalize_number_shapes(config):
            continue
        # Only the config changes, and nothing on the chart is derived from it,
        # so the write goes straight to the field and leaves `modified` where
        # the author left it.
        frappe.db.set_value(CHART, chart.name, "config", frappe.as_json(config), update_modified=False)
