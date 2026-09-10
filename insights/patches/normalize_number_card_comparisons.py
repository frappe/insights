import frappe

CHART = "Insights Chart v3"


def execute():
    """What a reading is measured against, written once in the shape the reader reads.

    Three releases have written it: a `target` and a `comparison` beside the
    reading, the `references` list before it, and a chart-level `comparison`
    flag before that, which said one previous-period comparison for every
    reading. Every chart is rewritten into the first shape, so nothing reads the
    other two any more.

    Idempotent — a chart that names no `references` and no chart-level flag is
    already in the shape and is left alone.
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
    """Every reading's target and comparison, written beside the reading, in
    place. Answers whether anything moved."""
    flag = config.pop("comparison", None)
    moved = flag is not None

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

    if columns:
        config["number_column_options"] = options

    return moved


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
