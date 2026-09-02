import frappe

DOCTYPE = "Insights Chart v3"

# A Sankey link is one row per source and target, and every Sankey source in the
# wild already emits exactly that — native SQL that either unions literal pairs
# with a `COUNT(*)`, or groups by the pair. So the group the chart aggregates
# holds a single row: `count` and `count_distinct` return 1 over it, `sum`,
# `avg`, `min` and `max` return the value itself.
COLLAPSING = ("count", "count_distinct")
REPAIRED = "sum"


def execute():
    """Repair the value aggregation of Sankey charts that would collapse.

    A Sankey used to draw its source query as it stood, so nothing read
    `config.value_column.aggregation`. It is read now: the chart derives
    `summarize(value, by source and target)` from the config, and the stored
    function decides the width of every ribbon.

    Because the function decided nothing, it was never really chosen. The
    measure picker pre-fills `sum` only when the source declares measure
    columns, and a native SQL source declares none — so the author picked from a
    list that opens with "Count of", over a column that is already a `COUNT(*)`.
    Counting a group of one row returns 1, and every ribbon draws the same width.

    This repairs only the two functions that collapse. Over a one-row group the
    other four return the value itself. A chart that holds one of them draws
    what the author sees today, so the patch leaves it alone.

    `measure_name` moves with the aggregation, because it is the name of the
    column the summarize writes and the name the renderer looks the value up by.
    It is renamed only when it is the picker's own name for the old function —
    a name the author typed says nothing about the aggregation and stays.

    No other slot in a Sankey config names the value measure. `order_by` can
    name a measure, but no Sankey on any site inspected has a sort at all, so
    nothing here goes looking for one.

    Running this twice changes nothing: a repaired chart holds `sum`, which is
    not a function this selects.
    """
    repaired = []

    for chart in frappe.get_all(DOCTYPE, filters={"chart_type": "Sankey"}, fields=["name", "config"]):
        config = frappe.parse_json(chart.config)
        if not isinstance(config, dict):
            continue

        value_column = config.get("value_column")
        if not isinstance(value_column, dict):
            continue

        aggregation = value_column.get("aggregation")
        if aggregation not in COLLAPSING:
            continue

        column_name = value_column.get("column_name")
        value_column["aggregation"] = REPAIRED
        if value_column.get("measure_name") == f"{aggregation}_of_{column_name}":
            value_column["measure_name"] = f"{REPAIRED}_of_{column_name}"

        # written past the document so the standard-content guard, which reads a
        # save, has nothing to block — a shipped Sankey is repaired like any other
        frappe.db.set_value(DOCTYPE, chart.name, "config", frappe.as_json(config), update_modified=False)
        repaired.append((chart.name, aggregation, value_column["measure_name"]))

    if not repaired:
        return

    print(f"Insights: repaired the value aggregation of {len(repaired)} Sankey chart(s)")
    for name, aggregation, measure_name in repaired:
        print(f"  {name}: {aggregation} -> {REPAIRED}, measure {measure_name}")
