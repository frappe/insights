import copy
import json
import math

import frappe

OLD_ROW_HEIGHT = 54
NEW_ROW_HEIGHT = 22

# A filter cell is as tall as the filter widget, whatever the grid's row is.
# The dashboard's cell rules own the height and restate it on every read, so
# this is the rows a cell is stored at and not the last word on them.
FILTER_ROWS = 2

# What a card holds decides how tall it is. `numberCardRows` in
# `charts/adapter/number.ts` owns the rule and restates it on every read, so
# these are the rows a cell is stored at and not the last word on them.
ROWS_TITLE_AND_VALUE = 4
ROWS_WITH_DELTA = 5
ROWS_WITH_SPARKLINE = 7


def execute():
    """The dashboard grid row went from 54px to 22px, so every stored box is in
    the wrong unit.

    22 is the row a Number card's three heights land on with the least waste;
    the reason lives beside `ROW_HEIGHT`. A cell keeps the pixels it covered,
    rounded up to the next whole row, so a card that fit its content still fits
    it. Two kinds of cell are not scaled but restated: a filter cell and a
    Number cell are as tall as what they draw, so each is written at the rows
    its own rule gives. Widths and columns are untouched: the grid still places
    against 20 of them.
    """
    configs = number_chart_configs()
    for name in frappe.get_all("Insights Dashboard v3", pluck="name"):
        items = frappe.db.get_value("Insights Dashboard v3", name, "items")
        rescaled = rescale_items(json.loads(items) if items else [], configs)
        if rescaled is None:
            continue
        frappe.db.set_value(
            "Insights Dashboard v3", name, "items", json.dumps(rescaled), update_modified=False
        )


def number_chart_configs() -> dict[str, dict]:
    """Every Number chart on the site, by name, with the config naming its readings."""
    charts = frappe.get_all("Insights Chart v3", filters={"chart_type": "Number"}, fields=["name", "config"])
    return {chart.name: frappe.parse_json(chart.config) or {} for chart in charts}


def rescale_items(items: list, configs: dict) -> list | None:
    """The items with every box in the new unit, or None when none moved.

    Rounding up is what keeps a card's content inside its cell, and it is also
    what can push two cells into each other — a row that was one cell's bottom
    edge and the next one's top rounds to two different rows. A cell written at
    its own rule instead of scaled leaves a gap under itself for the same
    reason. So the grid is settled and then pulled up afterwards, per
    breakpoint, the same way the reader lays it out.
    """
    before = copy.deepcopy(items)

    for item in items:
        rows = fixed_rows(item, configs)
        for box in _boxes(item):
            for side in ("y", "h"):
                value = box.get(side)
                if not isinstance(value, int | float):
                    continue
                box[side] = math.ceil(value * OLD_ROW_HEIGHT / NEW_ROW_HEIGHT)
            if rows:
                box["h"] = rows

    if items == before:
        return None

    settle_items(items)
    compact_items(items)

    return items


def fixed_rows(item: dict, configs: dict) -> int | None:
    """The rows a cell's own rule gives it, or None when its height is the
    author's."""
    if item.get("type") == "filter":
        return FILTER_ROWS
    if item.get("type") == "chart" and item.get("chart") in configs:
        return card_rows(configs[item["chart"]], item.get("column"))
    return None


def card_rows(config: dict, reading: str | None = None) -> int:
    """The rows one reading of a Number chart takes, in the three heights a card
    has. Naming no reading is naming the first, which is what such a cell draws."""
    if config.get("sparkline") and (config.get("date_column") or {}).get("column_name"):
        return ROWS_WITH_SPARKLINE
    return ROWS_WITH_DELTA if _compared(config, reading) else ROWS_TITLE_AND_VALUE


def number_readings(config: dict) -> list[str]:
    """The readings a Number chart states, in the order it states them."""
    columns = config.get("number_columns")
    if not isinstance(columns, list):
        return []
    return [c["measure_name"] for c in columns if isinstance(c, dict) and c.get("measure_name")]


def _compared(config: dict, reading: str | None) -> bool:
    """Whether the reading prints a delta row."""
    return bool(_options_of(config, reading).get("comparison"))


def _options_of(config: dict, reading: str | None) -> dict:
    """The settings beside a reading. They stand in a second list, by position."""
    columns = config.get("number_columns") or []
    index = next(
        (
            i
            for i, c in enumerate(columns)
            if isinstance(c, dict)
            and c.get("measure_name")
            and (reading is None or c["measure_name"] == reading)
        ),
        -1,
    )
    options = config.get("number_column_options")
    if not isinstance(options, list) or index < 0 or index >= len(options):
        return {}
    return options[index] if isinstance(options[index], dict) else {}


def settle_items(items: list) -> None:
    """Drop every cell past the ones above it, per breakpoint, the same way the
    reader settles the grid."""
    for boxes in _grids(items):
        _settle(boxes)


def compact_items(items: list) -> None:
    """Pull every cell up until it rests on one above it or on the top, per
    breakpoint, the same pass `compactLayouts` runs on every read."""
    for boxes in _grids(items):
        _compact(boxes)


def _grids(items: list) -> list[list[dict]]:
    """One list of boxes per breakpoint: the widest, and each narrower one."""
    grids = [[item["layout"] for item in items if isinstance(item.get("layout"), dict)]]
    for key in {key for item in items for key in (item.get("layouts") or {})}:
        grids.append(
            [
                (item.get("layouts") or {})[key]
                for item in items
                if isinstance((item.get("layouts") or {}).get(key), dict)
            ]
        )
    return grids


def _settle(boxes: list[dict]) -> None:
    """Drop every box past the ones above it, in place, in reading order."""
    placed: list[dict] = []
    for box in _reading_order(boxes):
        while True:
            hit = next((other for other in placed if _overlaps(box, other)), None)
            if not hit:
                break
            box["y"] = hit.get("y", 0) + hit.get("h", 0)
        placed.append(box)


def _compact(boxes: list[dict]) -> None:
    """Raise every box until it rests on one above it, in place, in reading order."""
    placed: list[dict] = []
    for box in _reading_order(boxes):
        y = box.get("y", 0)
        while y > 0 and not any(_overlaps({**box, "y": y - 1}, other) for other in placed):
            y -= 1
        box["y"] = y
        placed.append(box)


def _reading_order(boxes: list[dict]) -> list[dict]:
    return sorted(boxes, key=lambda b: (b.get("y", 0), b.get("x", 0)))


def _overlaps(a: dict, b: dict) -> bool:
    ax, aw, ay, ah = a.get("x", 0), a.get("w", 0), a.get("y", 0), a.get("h", 0)
    bx, bw, by, bh = b.get("x", 0), b.get("w", 0), b.get("y", 0), b.get("h", 0)
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def _boxes(item: dict):
    """Every box an item stores: the widest breakpoint, and each narrower one."""
    if isinstance(item.get("layout"), dict):
        yield item["layout"]
    for placement in (item.get("layouts") or {}).values():
        if isinstance(placement, dict):
            yield placement
