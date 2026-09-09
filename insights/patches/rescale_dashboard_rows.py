import json
import math

import frappe

OLD_ROW_HEIGHT = 54
NEW_ROW_HEIGHT = 22


def execute():
    """The dashboard grid row went from 54px to 22px, so every stored box is in
    the wrong unit.

    22 is the row a Number card's three heights land on with the least waste;
    the reason lives beside `ROW_HEIGHT`. Nothing else about a layout changes —
    a cell keeps the pixels it covered, rounded up to the next whole row, so a
    card that fit its content still fits it. Widths and columns are untouched:
    the grid still places against 20 of them.
    """
    for name in frappe.get_all("Insights Dashboard v3", pluck="name"):
        items = frappe.db.get_value("Insights Dashboard v3", name, "items")
        rescaled = rescale_items(json.loads(items) if items else [])
        if rescaled is None:
            continue
        frappe.db.set_value(
            "Insights Dashboard v3", name, "items", json.dumps(rescaled), update_modified=False
        )


def rescale_items(items: list) -> list | None:
    """The items with every box in the new unit, or None when none moved.

    Rounding up is what keeps a card's content inside its cell, and it is also
    what can push two cells into each other — a row that was one cell's bottom
    edge and the next one's top rounds to two different rows. So the grid is
    settled afterwards, per breakpoint, the same way the reader settles it.
    """
    moved = False
    for item in items:
        for box in _boxes(item):
            for side in ("y", "h"):
                value = box.get(side)
                if not isinstance(value, int | float):
                    continue
                scaled = math.ceil(value * OLD_ROW_HEIGHT / NEW_ROW_HEIGHT)
                if scaled != value:
                    box[side] = scaled
                    moved = True

    if not moved:
        return None

    settle_items(items)

    return items


def settle_items(items: list) -> None:
    """Drop every cell past the ones above it, per breakpoint, the same way the
    reader settles the grid."""
    _settle([item["layout"] for item in items if isinstance(item.get("layout"), dict)])
    for key in {key for item in items for key in (item.get("layouts") or {})}:
        _settle(
            [
                (item.get("layouts") or {})[key]
                for item in items
                if isinstance((item.get("layouts") or {}).get(key), dict)
            ]
        )


def _settle(boxes: list[dict]) -> None:
    """Drop every box past the ones above it, in place, in reading order."""
    placed: list[dict] = []
    for box in sorted(boxes, key=lambda b: (b.get("y", 0), b.get("x", 0))):
        while True:
            hit = next((other for other in placed if _overlaps(box, other)), None)
            if not hit:
                break
            box["y"] = hit.get("y", 0) + hit.get("h", 0)
        placed.append(box)


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
