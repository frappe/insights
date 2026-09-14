import copy
import math

import frappe

from insights.patches.resize_dashboard_cells import (
    card_rows,
    number_chart_configs,
    number_readings,
    settle_items,
)

# The widest a reading's card is made. On develop the readings drew in one cell
# on a grid of up to 5 per row, so a reading was 4 of the 20 columns wide.
READING_COLUMNS = 4


def execute():
    """A dashboard cell draws one reading, so a cell on a Number chart that
    states several becomes one cell per reading, sharing the width the one cell
    had.

    The chart is untouched: it keeps every reading, and each cell names the one
    it draws. Idempotent — a cell that already names a reading is left alone, so
    a second run finds nothing to expand.
    """
    configs = number_chart_configs()
    if not configs:
        return

    for name in frappe.get_all("Insights Dashboard v3", pluck="name"):
        stored = frappe.db.get_value("Insights Dashboard v3", name, "items")
        items = frappe.parse_json(stored)
        # a dashboard whose items are not a list is one this cannot read, and one
        # unreadable dashboard must not stop the migrate
        if not isinstance(items, list):
            continue
        if not expand_items(items, configs):
            continue
        # A reading that prints a delta row is taller than one that does not, so
        # the row can end lower than the one cell did and the cells under it
        # stand where it used to end. Settling drops them past it.
        settle_items(items)
        # `linked_charts` is derived from the items and needs no rebuild: it is
        # the charts the grid names, and this writes more cells on the same
        # charts. Nothing else about the dashboard is derived, so the write goes
        # straight to the field and leaves `modified` where the author left it.
        frappe.db.set_value(
            "Insights Dashboard v3", name, "items", frappe.as_json(items), update_modified=False
        )


def expand_items(items: list, configs: dict) -> bool:
    """Every cell on a multi-reading Number chart replaced by its readings' cells,
    in place. Answers whether anything moved."""
    # every id the grid already holds: `layout.i` keys the map the reader places
    # by, so a minted id that repeats one drops a cell
    taken = {(item.get("layout") or {}).get("i") for item in items if isinstance(item, dict)}

    moved = False
    position = 0
    while position < len(items):
        item = items[position]
        # one unreadable item must not stop the migrate, the same rule
        # `resize_dashboard_cells` states for a cell it cannot read
        if not isinstance(item, dict):
            position += 1
            continue
        cells = expand_item(item, configs, taken)
        if not cells:
            position += 1
            continue
        items[position : position + 1] = cells
        position += len(cells)
        moved = True
    return moved


def expand_item(item: dict, configs: dict, taken: set) -> list[dict] | None:
    """The cells one cell becomes, or None when it stays as it is.

    A cell drawing a chart that states one reading needs no name for it: naming
    none is naming the first, which is what it already drew.
    """
    if item.get("type") != "chart" or item.get("reading"):
        return None

    config = configs.get(item.get("chart"))
    readings = number_readings(config or {})
    if len(readings) < 2:
        return None

    heights = [card_rows(config, reading) for reading in readings]
    boxes = lay_out(item.get("layout") or {}, heights, READING_COLUMNS)
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
        cell["reading"] = reading
        cell["layout"] = boxes[index]
        cell["layout"]["i"] = _cell_id(item.get("layout") or {}, index, taken)
        taken.add(cell["layout"]["i"])
        if arranged is not None:
            cell["layouts"] = {key: arranged[key][index] for key in arranged}
        cells.append(cell)
    return cells


def lay_out(box: dict, heights: list[int], widest: int | None = None) -> list[dict]:
    """One cell per height, sharing the cell's width, all on the cell's row.

    The one cell's width is what the author gave the row, so the readings share
    it the way they shared the card: 7 columns for two readings is 4 and 3. No
    share is wider than `widest`, so a wide cell leaves its right end free, as
    an author narrowing the cards by hand would. A cell too narrow to give each
    reading a column gives them one each anyway — a cramped card is the
    author's to widen, and wrapping would move everything below instead.
    """
    left = box.get("w") or len(heights)
    x, y = box.get("x") or 0, box.get("y") or 0

    cells = []
    for index, height in enumerate(heights):
        width = max(1, math.ceil(left / (len(heights) - index)))
        if widest:
            width = min(width, widest)
        cell = dict(box)
        cell["x"] = x
        cell["y"] = y
        cell["w"] = width
        cell["h"] = height
        cells.append(cell)
        x += width
        left -= width
    return cells


def _cell_id(layout: dict, index: int, taken: set) -> str:
    """The first cell keeps the id, so an arrangement that named it still finds it.

    The rest count up from it, past every id the grid already holds.
    """
    i = layout.get("i") or frappe.generate_hash(length=8)
    if index == 0:
        return i

    suffix = index + 1
    while f"{i}-{suffix}" in taken:
        suffix += 1
    return f"{i}-{suffix}"
