import frappe

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
        config = frappe.parse_json(chart.config) or {}
        if not normalize(config):
            continue
        # Only the config changes, and nothing on the chart is derived from it,
        # so the write goes straight to the field and leaves `modified` where
        # the author left it.
        frappe.db.set_value(CHART, chart.name, "config", frappe.as_json(config), update_modified=False)


def normalize(config: dict) -> bool:
    """The card's period, and every reading's target and comparison, written
    where the card reads them, in place. Answers whether anything moved."""
    flag = config.pop("comparison", None)
    moved = raise_period(config) or flag is not None

    columns = config.get("number_columns") or []
    options = config.get("number_column_options")
    if not isinstance(options, list):
        options = []

    for index in range(len(columns)):
        while len(options) <= index:
            options.append({})
        beside = options[index] if isinstance(options[index], dict) else {}
        options[index] = beside

        measured = measured_against(beside, flag)
        if beside.pop("references", None) is not None:
            moved = True
        for key in ("target", "comparison"):
            if measured.get(key) and not beside.get(key):
                beside[key] = measured[key]
                moved = True

        moved = normalize_comparison(beside) or moved

    if columns:
        config["number_column_options"] = options

    return moved


def raise_period(config: dict) -> bool:
    """The period the card reads, moved off the date column and onto the chart.

    A granularity on the date column used to group the card, and `window` does
    that now. Both at once would group twice, so the granularity goes wherever
    a period is named — lifted into one when the chart names none.
    """
    date_column = config.get("date_column")
    if not isinstance(date_column, dict) or not date_column.get("granularity"):
        return False

    window = config.get("window") or {}
    if not window.get("span") and not window.get("grain"):
        config["window"] = {**window, "grain": date_column["granularity"]}

    # deleted, not set to `None`: a config is stored as JSON, so a key with no
    # value is a key the next load will not have
    del date_column["granularity"]
    return True


def normalize_comparison(options: dict) -> bool:
    """A period comparison, written as the question it asks.

    A `window` comparison carried the shift that fetched it, which the period
    the card read at the time decided. The period decides that where the card is
    read now, so the shift is dropped and only the question is kept: the same
    span a year back is `last year`, and every other shift is the period before
    this one.
    """
    comparison = options.get("comparison")
    if not isinstance(comparison, dict) or comparison.get("source") != "window":
        return False

    shift = comparison.pop("shift", None) or {}
    year_back = shift.get("unit") in ("year", "fiscal year") and shift.get("count") == -1
    comparison["source"] = "last year" if year_back else "previous"
    return True


def measured_against(options: dict, flag) -> dict:
    """What the reading is measured against, read the way the card reads it:
    what the reading names, else the `references` it named, else the chart's
    flag."""
    if options.get("target") or options.get("comparison"):
        return {}

    references = options.get("references")
    if isinstance(references, list):
        return from_references(references)

    return {"comparison": {"source": "previous"}} if flag else {}


def from_references(references: list) -> dict:
    """A movement in the list is the comparison, an attainment the target."""

    def moves(reference: dict) -> bool:
        return reference.get("show") in ("change", "delta") or reference.get("source") == "previous"

    references = [r for r in references if isinstance(r, dict)]
    leading = next((i for i, r in enumerate(references) if moves(r)), -1)
    aim = next(
        (i for i, r in enumerate(references) if i != leading and r.get("show") == "attainment"),
        -1,
    )

    measured = {}
    if leading != -1:
        reference = references[leading]
        comparison = {"source": reference.get("source")}
        if reference.get("value") is not None:
            comparison["value"] = reference["value"]
        if reference.get("measure"):
            comparison["measure"] = reference["measure"]
        comparison["show"] = "delta" if reference.get("show") == "delta" else "change"
        if reference.get("label"):
            comparison["label"] = reference["label"]
        measured["comparison"] = comparison
    if aim != -1:
        reference = references[aim]
        measured["target"] = (
            {"measure": reference["measure"]}
            if reference.get("measure")
            else {"value": reference.get("value")}
        )

    return measured
