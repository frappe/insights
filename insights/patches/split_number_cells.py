import copy

import frappe

from insights.patches.rescale_dashboard_rows import settle_items

# What a card holds decides how tall it is. `numberCardRows` in
# `charts/adapter/number.ts` owns the rule and restates it on every read, so
# these are the rows a cell starts at and not the last word on them.
ROWS_TITLE_AND_VALUE = 4
ROWS_WITH_DELTA = 5
ROWS_WITH_SPARKLINE = 7

# The columns a dropped cell starts at, a fifth of the grid: the width the old
# inner grid gave a card in a full-width cell, and `addChart` gives one now.
CELL_COLUMNS = 4


def execute():
    """A dashboard cell draws one reading, so a cell on a Number chart that
    states several becomes one cell per reading, laid left to right inside the
    width the one cell had.

    The chart is untouched: it keeps every reading, and each cell names the one
    it draws. Idempotent — a cell that already names a reading is left alone, so
    a second run finds nothing to expand.
    """
    configs = number_chart_configs()
    if not configs:
        return

    for name in frappe.get_all("Insights Dashboard v3", pluck="name"):
        stored = frappe.db.get_value("Insights Dashboard v3", name, "items")
        items = frappe.parse_json(stored) or []
        if not expand_items(items, configs):
            continue
        # One cell became several taller ones, so the cells under it are where
        # the one cell used to end. Settling drops them past their new
        # neighbours, the same pass `rescale_dashboard_rows` runs for the same
        # reason.
        settle_items(items)
        # `linked_charts` is derived from the items and needs no rebuild: it is
        # the charts the grid names, and this writes more cells on the same
        # charts. Nothing else about the dashboard is derived, so the write goes
        # straight to the field and leaves `modified` where the author left it.
        frappe.db.set_value(
            "Insights Dashboard v3", name, "items", frappe.as_json(items), update_modified=False
        )


def number_chart_configs() -> dict[str, dict]:
    """Every Number chart on the site, by name, with the config naming its readings."""
    charts = frappe.get_all("Insights Chart v3", filters={"chart_type": "Number"}, fields=["name", "config"])
    return {chart.name: frappe.parse_json(chart.config) or {} for chart in charts}


def expand_items(items: list, configs: dict) -> bool:
    """Every cell on a multi-reading Number chart replaced by its readings' cells,
    in place. Answers whether anything moved."""
    moved = False
    position = 0
    while position < len(items):
        cells = expand_item(items[position], configs)
        if not cells:
            position += 1
            continue
        items[position : position + 1] = cells
        position += len(cells)
        moved = True
    return moved


def expand_item(item: dict, configs: dict) -> list[dict] | None:
    """The cells one cell becomes, or None when it stays as it is.

    A cell drawing a chart that states one reading needs no name for it: naming
    none is naming the first, which is what it already drew.
    """
    if item.get("type") != "chart" or item.get("column"):
        return None

    config = configs.get(item.get("chart"))
    readings = number_readings(config or {})
    if len(readings) < 2:
        return None

    heights = [card_rows(config, reading) for reading in readings]
    boxes = lay_out(item.get("layout") or {}, heights)
    arranged = (
        {
            key: lay_out(box, heights)
            for key, box in (item.get("layouts") or {}).items()
            if isinstance(box, dict)
        }
        if isinstance(item.get("layouts"), dict)
        else None
    )

    cells = []
    for index, reading in enumerate(readings):
        cell = copy.deepcopy(item)
        cell["column"] = reading
        cell["layout"] = boxes[index]
        cell["layout"]["i"] = _cell_id(item.get("layout") or {}, index)
        if arranged is not None:
            cell["layouts"] = {key: arranged[key][index] for key in arranged}
        cells.append(cell)
    return cells


def number_readings(config: dict) -> list[str]:
    """The readings a Number chart states, in the order it states them."""
    columns = config.get("number_columns")
    if not isinstance(columns, list):
        return []
    return [c["measure_name"] for c in columns if isinstance(c, dict) and c.get("measure_name")]


def card_rows(config: dict, reading: str) -> int:
    """The rows one reading takes, in the three heights a card has."""
    if config.get("sparkline") and (config.get("date_column") or {}).get("column_name"):
        return ROWS_WITH_SPARKLINE
    return ROWS_WITH_DELTA if _compared(config, reading) else ROWS_TITLE_AND_VALUE


def _compared(config: dict, reading: str) -> bool:
    """Whether the reading prints a delta row.

    The three shapes `measuredAgainst` reads, in its order: a comparison the
    reading names, the `references` list a release before it wrote, and the
    chart-level flag that said one previous-period comparison for every reading.
    """
    options = _options_of(config, reading)
    if options.get("target") or options.get("comparison"):
        return bool(options.get("comparison"))

    references = options.get("references")
    if isinstance(references, list):
        return any(
            r.get("show") in ("change", "delta") or r.get("source") == "previous"
            for r in references
            if isinstance(r, dict)
        )

    return bool(config.get("comparison"))


def _options_of(config: dict, reading: str) -> dict:
    """The settings beside a reading. They stand in a second list, by position."""
    columns = config.get("number_columns") or []
    index = next(
        (i for i, c in enumerate(columns) if isinstance(c, dict) and c.get("measure_name") == reading),
        -1,
    )
    options = config.get("number_column_options")
    if not isinstance(options, list) or index < 0 or index >= len(options):
        return {}
    return options[index] if isinstance(options[index], dict) else {}


def lay_out(box: dict, heights: list[int]) -> list[dict]:
    """One cell per height, each the width a dropped cell takes, laid left to
    right from the cell's corner and wrapping inside its width.

    The one cell's width is what the author gave the row, so the cells fill it
    the way the readings did before, and a row that overflows it starts another
    under the tallest cell of the one above. A cell narrower than a dropped cell
    gives each reading its whole width, one under the other.
    """
    width = min(CELL_COLUMNS, box.get("w") or CELL_COLUMNS)
    per_row = max(1, (box.get("w") or width) // width)
    x0, y0 = box.get("x") or 0, box.get("y") or 0

    cells = []
    y = y0
    for index, height in enumerate(heights):
        row, column = divmod(index, per_row)
        if column == 0 and row > 0:
            y += max(heights[(row - 1) * per_row : row * per_row])
        cell = dict(box)
        cell["x"] = x0 + column * width
        cell["y"] = y
        cell["w"] = width
        cell["h"] = height
        cells.append(cell)
    return cells


def _cell_id(layout: dict, index: int) -> str:
    """The first cell keeps the id, so an arrangement that named it still finds it."""
    i = layout.get("i") or frappe.generate_hash(length=8)
    return i if index == 0 else f"{i}-{index + 1}"
