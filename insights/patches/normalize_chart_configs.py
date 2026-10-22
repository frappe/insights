import frappe

from insights.insights.doctype.insights_chart_v3.chart_query import normalize_chart_config
from insights.upgrade import add_item

CHART = "Insights Chart v3"
# what Insights before 3.50 showed with no `max_slices`
DONUT_SLICES = 10
STATISTIC_NAMES = {
    "average": "average",
    "median": "median",
    "min": "minimum",
    "max": "maximum",
    "sum": "total",
}


def execute():
    """Every stored chart config in the shape the readers read, written once.

    Runs `normalize_chart_config` over every stored config. See its docstring
    for why. Then `draw_as_insights_3` writes what Insights before 3.50 assumed on load
    and Insights 3.50 reads from the config. It belongs here and not in
    `normalize_chart_config`: that runs on every save, and a chart saved on
    Insights 3.50 means what it says. A site that already ran this patch keeps
    what it showed since.

    Idempotent: a chart already in the shape is not written.
    """
    for chart in frappe.get_all(CHART, fields=["name", "title", "owner", "config", "chart_type"]):
        config = frappe.parse_json(chart.config)
        if not isinstance(config, dict):
            continue

        written = normalize_chart_config(config, chart.chart_type)
        title = chart.title or chart.name
        for code, message, data in [
            *draw_as_insights_3(written, chart.chart_type, title),
            *statistic_lines_moved(config, written, title),
        ]:
            add_item(
                code,
                message,
                reference=(CHART, chart.name),
                user=None if chart.owner == "Administrator" else chart.owner,
                data=data,
            )
        if written == config:
            continue

        # Nothing on the chart is derived from its config, so this keeps
        # `modified` where the author left it.
        frappe.db.set_value(CHART, chart.name, "config", frappe.as_json(written), update_modified=False)


def draw_as_insights_3(config: dict, chart_type: str, title: str) -> list[tuple[str, str, dict]]:
    """Write into `config` what Insights before 3.50 drew it with, in place. Answers the
    `(code, message, data)` of each thing it could not keep."""
    y_axis = config.get("y_axis")
    if chart_type == "Bar" and isinstance(y_axis, dict) and "stack" not in y_axis:
        # C1: Insights before 3.50 stacked a Bar that stated nothing on load
        y_axis["stack"] = True
    if chart_type == "Line" and isinstance(y_axis, dict):
        # C2: Insights before 3.50 never read these on a Line. They are left from the Bar
        # every new chart started as, and Insights 3.50 stacks a Line by them.
        for key in ("stack", "normalize", "overlap"):
            y_axis.pop(key, None)
    if chart_type == "Donut":
        # C7: Insights before 3.50 drew this many slices and then Others. Insights 3.50 counts
        # Others among them.
        slices = config.get("max_slices")
        config["max_slices"] = (int(slices) if is_count(slices) else DONUT_SLICES) + 1
    if chart_type == "Number":
        return [*number_units_as_insights_3(config, title), *number_period_as_insights_3(config, title)]
    return []


def statistic_lines_moved(config: dict, written: dict, title: str) -> list[tuple[str, str, dict]]:
    """C4: a reference line at a statistic read every value Insights before 3.50 plotted on
    its axis, stack totals included. `normalize_chart_config` points it at the
    first series on that axis, which differs once the axis plots more than one
    series, and leaves no line on a chart that plots only the count."""
    before, after = config.get("y_axis"), written.get("y_axis")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return []
    series = [s for s in after.get("series") or [] if isinstance(s, dict)]
    split_by = written.get("split_by")
    split = isinstance(split_by, dict) and ((split_by.get("dimension") or {}).get("column_name"))
    lines = []
    for old, new in zip(
        before.get("reference_lines") or [], after.get("reference_lines") or [], strict=False
    ):
        if not isinstance(old, dict) or not old.get("statistic") or not isinstance(new, dict):
            continue
        name = STATISTIC_NAMES.get(old["statistic"], old["statistic"])
        align = "Right" if new.get("align") == "Right" else "Left"
        on_axis = [s for s in series if (s.get("align") or "Left") == align]
        if not new.get("measure_name"):
            lines.append({"statistic": name, "removed": True, "measure": None})
        elif len(on_axis) > 1 or split:
            lines.append({"statistic": name, "removed": False, "measure": new["measure_name"]})
    if not lines:
        return []
    found = [
        f"{line['statistic']} line removed, as the chart plots only the count"
        if line["removed"]
        else f"{line['statistic']} line reads {line['measure']} only"
        for line in lines
    ]
    return [("C4", f'"{title}": {"; ".join(found)}', {"chart": title, "lines": lines})]


def is_count(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and value >= 1


def number_units_as_insights_3(config: dict, title: str) -> list[tuple[str, str, dict]]:
    """N4: each reading's prefix and suffix, printed with its unit as Insights before 3.50 did.

    Insights before 3.50 read a reading's own prefix and suffix, else the card's. A prefix
    replaced the unit's, and a blank one left it. A suffix printed after the
    unit's. Insights 3.50 prints whatever a reading states in place of the unit,
    blank included, so a blank is dropped and a suffix holds the unit's.
    """
    columns = config.get("number_columns")
    options = config.get("number_column_options")
    if not isinstance(columns, list) or not isinstance(options, list):
        return []

    card = {key: config.pop(key) for key in ("prefix", "suffix") if key in config}
    found = []
    for column, option in zip(columns, options, strict=False):
        if not isinstance(option, dict):
            continue
        prefix, suffix = (option.get(key) if key in option else card.get(key) for key in ("prefix", "suffix"))
        option.pop("prefix", None)
        option.pop("suffix", None)
        if prefix:
            option["prefix"] = prefix
        if not suffix:
            continue

        unit = column.get("format") if isinstance(column, dict) else None
        if unit == "percent":
            suffix = f"%{suffix}"
        elif unit == "currency" and (config.get("currency_column") or symbol_on_right()):
            found.append(("N4", f'"{title}", suffix "{suffix}"', {"chart": title, "suffix": suffix}))
        option["suffix"] = suffix
    return found


def symbol_on_right() -> bool:
    currency = frappe.db.get_default("currency")
    return bool(currency and frappe.db.get_value("Currency", currency, "symbol_on_right"))


def number_period_as_insights_3(config: dict, title: str) -> list[tuple[str, str, dict]]:
    """N5 and N6: the period a card on a date column read in Insights before 3.50.

    Insights before 3.50 grouped a card by its date column, by the granularity when it had
    one, and showed the last group. Insights 3.50 groups a card only by a period, so
    a card with none shows the total. A day is the period that keeps a Date's
    groups. Insights 3.50 has no period for a time of day, so a Time card shows the
    total and is reported.
    """
    date_column = config.get("date_column")
    window = config.get("window") or {}
    if (
        not isinstance(date_column, dict)
        or not date_column.get("column_name")
        or not isinstance(window, dict)
    ):
        return []

    column, data_type = date_column["column_name"], date_column.get("data_type")
    if data_type == "Time":
        window.pop("grain", None)
        if window:
            config["window"] = window
        else:
            config.pop("window", None)
        return [("N6", f'"{title}" on {column}', {"chart": title, "column": column})]

    if window.get("span") or window.get("grain"):
        return []
    config["window"] = {**window, "grain": "day"}
    if data_type != "Datetime":
        return []
    return [("N5", f'"{title}" on {column}', {"chart": title, "column": column})]
