"""The one-time rewrite of every dashboard box when the grid row changed.

Every box is scaled into the new row, a filter cell and a Number cell are
written at the rows their own rules give them, and the grid is settled and
pulled up afterwards. See `insights/patches/resize_dashboard_cells.py`.
"""

import unittest

from insights.patches.resize_dashboard_cells import compact_items, rescale_items


def chart_cell(i, chart="c", **layout):
    return {"type": "chart", "chart": chart, "layout": {"i": i, "x": 0, "y": 0, "w": 4, "h": 4, **layout}}


def filter_cell(i, **layout):
    return {
        "type": "filter",
        "filter_name": "Company",
        "layout": {"i": i, "x": 0, "y": 0, "w": 4, "h": 1, **layout},
    }


def text_cell(i, **layout):
    return {"type": "text", "text": "hi", "layout": {"i": i, "x": 0, "y": 0, "w": 4, "h": 1, **layout}}


def number_config(*readings, options=None, **rest):
    return {
        "number_columns": [{"measure_name": name} for name in readings],
        "number_column_options": options or [{} for _ in readings],
        **rest,
    }


def boxes(items):
    return [item["layout"] for item in items]


class TestRescaleItems(unittest.TestCase):
    def test_a_box_keeps_the_pixels_it_covered(self):
        items = [text_cell("t", y=2, h=3), text_cell("u", y=5, h=1)]

        rescaled = rescale_items(items, {})

        self.assertEqual([(b["y"], b["h"]) for b in boxes(rescaled)], [(0, 8), (8, 3)])

    def test_a_filter_cell_is_two_rows(self):
        items = [filter_cell("f", h=1), filter_cell("g", x=4, h=1)]

        rescaled = rescale_items(items, {})

        self.assertEqual([b["h"] for b in boxes(rescaled)], [2, 2])

    def test_a_number_cell_is_as_tall_as_its_card(self):
        configs = {
            "plain": number_config("Revenue"),
            "compared": number_config("Churn", options=[{"comparison": {"source": "previous"}}]),
            "trending": number_config("Spend", sparkline=True, date_column={"column_name": "posting_date"}),
        }
        items = [
            chart_cell("a", chart="plain", h=8),
            chart_cell("b", chart="compared", x=4, h=8, column="Churn"),
            chart_cell("c", chart="trending", x=8, h=8),
        ]

        rescaled = rescale_items(items, configs)

        self.assertEqual([b["h"] for b in boxes(rescaled)], [4, 5, 7])

    def test_a_cell_on_no_number_chart_is_only_scaled(self):
        items = [chart_cell("a", chart="bar", h=8)]

        rescaled = rescale_items(items, {})

        self.assertEqual(boxes(rescaled)[0]["h"], 20)

    def test_every_breakpoint_the_cell_was_arranged_for_is_rewritten(self):
        items = [filter_cell("f", h=1)]
        items[0]["layouts"] = {"sm": {"x": 0, "y": 0, "w": 20, "h": 1}}

        rescaled = rescale_items(items, {})

        self.assertEqual(rescaled[0]["layouts"]["sm"]["h"], 2)

    def test_the_cells_under_a_shortened_one_come_up_to_meet_it(self):
        items = [
            filter_cell("f", y=0, h=1),
            chart_cell("a", chart="plain", y=1, h=4),
        ]

        rescaled = rescale_items(items, {"plain": number_config("Revenue")})

        self.assertEqual([(b["y"], b["h"]) for b in boxes(rescaled)], [(0, 2), (2, 4)])

    def test_a_grid_with_nothing_on_it_is_left_alone(self):
        self.assertIsNone(rescale_items([], {}))


class TestCompactItems(unittest.TestCase):
    def test_a_cell_rises_until_it_rests_on_the_one_above_it(self):
        items = [text_cell("a", y=2, h=3), text_cell("b", y=9, h=2)]

        compact_items(items)

        self.assertEqual([b["y"] for b in boxes(items)], [0, 3])

    def test_cells_side_by_side_rise_past_each_other(self):
        items = [text_cell("a", x=0, y=4, h=3), text_cell("b", x=4, y=9, h=2)]

        compact_items(items)

        self.assertEqual([b["y"] for b in boxes(items)], [0, 0])

    def test_a_compact_grid_does_not_move(self):
        items = [text_cell("a", y=0, h=3), text_cell("b", y=3, h=2)]

        compact_items(items)

        self.assertEqual([b["y"] for b in boxes(items)], [0, 3])
