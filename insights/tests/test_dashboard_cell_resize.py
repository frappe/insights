"""The one-time rewrite of every dashboard box when the grid row changed.

Every box is scaled into the new row, a filter cell and a Number cell are
written at the rows their own rules give them, and the grid is settled where it
stands. See `insights/patches/resize_dashboard_cells.py`.
"""

import unittest
from unittest.mock import patch

import frappe

from insights.patches import resize_dashboard_cells
from insights.patches.resize_dashboard_cells import already_rescaled, rescale_items
from insights.tests.base import InsightsIntegrationTestCase


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
    # @feature upgrade.older-grid-read
    def test_a_box_keeps_the_pixels_it_covered(self):
        """Top and height are scaled alike, so the grid comes out where it was:
        the first cell stood at 104px and stands at 110px."""
        items = [text_cell("t", y=2, h=3), text_cell("u", y=5, h=1)]

        rescaled = rescale_items(items, {})

        self.assertEqual([(b["y"], b["h"]) for b in boxes(rescaled)], [(5, 8), (13, 3)])

    # @feature upgrade.older-grid-read
    def test_a_filter_cell_is_two_rows(self):
        items = [filter_cell("f", h=1), filter_cell("g", x=4, h=1)]

        rescaled = rescale_items(items, {})

        self.assertEqual([b["h"] for b in boxes(rescaled)], [2, 2])

    # @feature upgrade.older-grid-read
    def test_a_number_cell_is_as_tall_as_its_card(self):
        configs = {
            "plain": number_config("Revenue"),
            "compared": number_config("Churn", options=[{"comparison": {"source": "previous"}}]),
            "trending": number_config(
                "Spend",
                sparkline=True,
                date_column={"column_name": "posting_date"},
                window={"span": "last 3 months"},
            ),
        }
        items = [
            chart_cell("a", chart="plain", h=8),
            chart_cell("b", chart="compared", x=4, h=8, reading="Churn"),
            chart_cell("c", chart="trending", x=8, h=8),
        ]

        rescaled = rescale_items(items, configs)

        self.assertEqual([b["h"] for b in boxes(rescaled)], [4, 5, 7])

    # @feature upgrade.older-grid-read
    def test_a_grain_card_keeps_its_sparkline_band(self):
        """The card's own rule and not the server's: a grain card draws its own
        readings as the series, so the band is there and the cell holds it."""
        configs = {
            "latest": number_config(
                "Spend",
                sparkline=True,
                date_column={"column_name": "posting_date"},
                window={"grain": "month"},
            )
        }
        items = [chart_cell("a", chart="latest", h=8)]

        rescaled = rescale_items(items, configs)

        self.assertEqual(boxes(rescaled)[0]["h"], 7)

    # @feature upgrade.older-grid-read
    def test_a_card_whose_date_column_is_not_a_shape_it_reads_is_only_scaled(self):
        """One unreadable config must not abort the migrate."""
        configs = {"odd": number_config("Spend", sparkline=True, date_column="posting_date")}
        items = [chart_cell("a", chart="odd", h=8)]

        rescaled = rescale_items(items, configs)

        self.assertEqual(boxes(rescaled)[0]["h"], 4)

    # @feature upgrade.older-grid-read
    def test_a_cell_on_no_number_chart_is_only_scaled(self):
        items = [chart_cell("a", chart="bar", h=8)]

        rescaled = rescale_items(items, {})

        self.assertEqual(boxes(rescaled)[0]["h"], 19)

    # @feature upgrade.older-grid-read
    def test_every_breakpoint_the_cell_was_arranged_for_is_rewritten(self):
        items = [filter_cell("f", h=1)]
        items[0]["layouts"] = {"sm": {"x": 0, "y": 0, "w": 20, "h": 1}}

        rescaled = rescale_items(items, {})

        self.assertEqual(rescaled[0]["layouts"]["sm"]["h"], 2)

    # @feature upgrade.older-grid-read
    def test_a_gap_the_rescale_opens_is_left_open(self):
        """Scaling a row up rounds, and a rounded cell can leave a gap under itself.
        Closing it would also close the gaps the author meant, and nothing stored
        tells the two apart."""
        items = [
            filter_cell("f", y=0, h=1),
            chart_cell("a", chart="plain", y=1, h=4),
        ]

        rescaled = rescale_items(items, {"plain": number_config("Revenue")})

        self.assertEqual([(b["y"], b["h"]) for b in boxes(rescaled)], [(0, 2), (3, 4)])

    # @feature upgrade.older-grid-read
    def test_one_unreadable_item_does_not_stop_the_rescale(self):
        items = ["not an item", text_cell("t", y=2, h=3)]

        rescaled = rescale_items(items, {})

        self.assertEqual(rescaled[1]["layout"]["h"], 8)

    # @feature upgrade.older-grid-read
    def test_an_unreadable_layouts_does_not_stop_the_rescale(self):
        items = [
            {
                "type": "text",
                "text": "hi",
                "layout": {"i": "t", "x": 0, "y": 2, "w": 4, "h": 3},
                "layouts": [],
            },
        ]

        rescaled = rescale_items(items, {})

        self.assertEqual(rescaled[0]["layout"]["h"], 8)

    # @feature upgrade.older-grid-read
    def test_a_grid_with_nothing_on_it_is_left_alone(self):
        self.assertIsNone(rescale_items([], {}))


class TestAlreadyRescaled(InsightsIntegrationTestCase):
    """The guard that stands between a re-run and every box doubling."""

    PATCH = "insights.patches.probe_rescale"

    def before_test(self):
        self.enterContext(patch.object(resize_dashboard_cells, "PATCH", self.PATCH))

    def after_test(self):
        frappe.db.delete("Patch Log", {"patch": ("like", "insights.patches.probe%")})

    def log(self, patch_name, skipped=0):
        frappe.get_doc({"doctype": "Patch Log", "patch": patch_name, "skipped": skipped}).insert()

    # @feature upgrade.older-grid-read
    def test_a_run_that_landed_stops_the_next_one(self):
        self.log(self.PATCH)
        self.assertTrue(already_rescaled())

    # @feature upgrade.older-grid-read
    def test_a_re_run_under_a_suffix_is_the_same_run(self):
        self.log(f"{self.PATCH} #2")
        self.assertTrue(already_rescaled())

    # @feature upgrade.older-grid-read
    def test_a_skipped_run_leaves_the_retry_open(self):
        # `migrate --skip-failing` logs a skipped row after rolling the data back
        self.log(f"{self.PATCH} #2", skipped=1)
        self.assertFalse(already_rescaled())

    # @feature upgrade.older-grid-read
    def test_another_patch_is_not_read_as_this_one(self):
        # the underscores in the module path are not single-character wildcards
        self.log("insights.patches.probeXrescale #2")
        self.assertFalse(already_rescaled())
