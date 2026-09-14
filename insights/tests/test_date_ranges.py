from unittest.mock import patch

from frappe.utils.data import get_date_str, getdate
from sqlalchemy import column as sa_column

from insights.insights.query_builders.sql_functions import (
    get_date_range,
    get_window,
    handle_timespan,
    shift_anchor,
)
from insights.tests.base import InsightsIntegrationTestCase

# 2022-11-26 is a Saturday
NOW = "insights.insights.query_builders.sql_functions.nowdate"

# 2026-08-10 is a Monday
ANCHOR = getdate("2026-08-10")

# timespans are already lowercased and singularised by handle_timespan


class TestWeekDateRanges(InsightsIntegrationTestCase):
    def assert_ranges(self, expected, include_current=False):
        with patch(NOW, return_value="2022-11-26"):
            for timespan, dates in expected.items():
                result = [get_date_str(d) for d in get_date_range(timespan, include_current)]
                self.assertEqual(result, dates, timespan)

    # @feature settings.week-start
    def test_week_ranges_start_on_monday(self):
        with self.change_settings("Insights Settings", week_starts_on="Monday"):
            self.assert_ranges(
                {
                    "current week": ["2022-11-21", "2022-11-27"],
                    "last 1 week": ["2022-11-14", "2022-11-20"],
                    "last 5 week": ["2022-10-17", "2022-11-20"],
                    "next 1 week": ["2022-11-28", "2022-12-04"],
                }
            )

    # @feature settings.week-start
    def test_week_ranges_follow_the_configured_start_day(self):
        with self.change_settings("Insights Settings", week_starts_on="Sunday"):
            self.assert_ranges(
                {
                    "current week": ["2022-11-20", "2022-11-26"],
                    "last 1 week": ["2022-11-13", "2022-11-19"],
                    "last 5 week": ["2022-10-16", "2022-11-19"],
                    "next 1 week": ["2022-11-27", "2022-12-03"],
                }
            )

    # @feature query.filter-relative-date-include-current
    def test_include_current_extends_to_this_week(self):
        with self.change_settings("Insights Settings", week_starts_on="Monday"):
            self.assert_ranges(
                {
                    "last 1 week": ["2022-11-14", "2022-11-27"],
                    "next 1 week": ["2022-11-21", "2022-12-04"],
                },
                include_current=True,
            )


class TestToDateWindows(InsightsIntegrationTestCase):
    # @feature charts.number-period
    def test_a_to_date_window_ends_at_the_anchor(self):
        with self.change_settings(
            "Insights Settings", week_starts_on="Sunday", fiscal_year_start="2020-04-01"
        ):
            expected = {
                "day to date": ["2026-08-10", "2026-08-10"],
                "week to date": ["2026-08-09", "2026-08-10"],
                "month to date": ["2026-08-01", "2026-08-10"],
                "quarter to date": ["2026-07-01", "2026-08-10"],
                "year to date": ["2026-01-01", "2026-08-10"],
                "fiscal year to date": ["2026-04-01", "2026-08-10"],
            }
            for span, dates in expected.items():
                result = [get_date_str(d) for d in get_window(span, ANCHOR)]
                self.assertEqual(result, dates, span)

    # @feature charts.number-period
    def test_on_the_last_day_of_a_period_it_equals_the_whole_period(self):
        with self.change_settings("Insights Settings", fiscal_year_start="2020-04-01"):
            last_days = {
                "month": "2026-08-31",
                "quarter": "2026-09-30",
                "year": "2026-12-31",
                "fiscal year": "2027-03-31",
            }
            for unit, last_day in last_days.items():
                anchor = getdate(last_day)
                self.assertEqual(
                    get_window(f"{unit} to date", anchor),
                    get_window(f"current {unit}", anchor),
                    unit,
                )

    # @feature charts.number-period
    def test_the_old_spans_are_unchanged(self):
        with self.change_settings("Insights Settings", week_starts_on="Monday"):
            spans = [
                "current day",
                "current week",
                "current month",
                "current quarter",
                "current year",
                "last 7 day",
                "last 3 month",
                "next 1 quarter",
            ]
            for span in spans:
                self.assertEqual(
                    get_window(span, ANCHOR),
                    tuple(get_date_range(span, anchor=ANCHOR)),
                    span,
                )

    # @feature charts.number-period
    def test_an_unknown_unit_is_rejected(self):
        with self.assertRaises(Exception):
            get_window("fortnight to date", ANCHOR)

    # @feature charts.number-period
    def test_a_counted_span_to_date_is_rejected(self):
        """A period so far is one period. "last 7 days to date" names a count the
        shape cannot carry, and reading it as today would drop the count."""
        with self.assertRaises(Exception):
            get_window("last 7 days to date", ANCHOR)


class TestShiftAnchor(InsightsIntegrationTestCase):
    # @feature query.filter-relative-date-shift
    def test_every_unit_moves_the_anchor(self):
        shifts = {
            ("day", -1): "2026-08-09",
            ("week", -1): "2026-08-03",
            ("month", -1): "2026-07-10",
            ("quarter", -1): "2026-05-10",
            ("year", -1): "2025-08-10",
            ("fiscal year", -1): "2025-08-10",
            ("month", 2): "2026-10-10",
        }
        for (unit, count), expected in shifts.items():
            self.assertEqual(shift_anchor(ANCHOR, unit, count), getdate(expected), unit)

    # @feature query.filter-relative-date-shift
    def test_a_leap_day_lands_on_the_last_day_of_february(self):
        leap_day = getdate("2024-02-29")
        self.assertEqual(shift_anchor(leap_day, "year", -1), getdate("2023-02-28"))
        self.assertEqual(shift_anchor(leap_day, "year", 1), getdate("2025-02-28"))

    # @feature query.filter-relative-date-shift
    def test_a_month_end_lands_inside_a_shorter_month(self):
        self.assertEqual(shift_anchor(getdate("2026-03-31"), "month", -1), getdate("2026-02-28"))
        self.assertEqual(shift_anchor(getdate("2026-01-31"), "month", 1), getdate("2026-02-28"))

    # @feature charts.number-period
    def test_the_window_is_recomputed_from_the_moved_anchor(self):
        # the start stays at the year, which a shift of the endpoints would move
        self.assertEqual(
            get_window("year to date", shift_anchor(ANCHOR, "month", -1)),
            (getdate("2026-01-01"), getdate("2026-07-10")),
        )

    # @feature charts.number-period
    def test_a_shifted_to_date_window_stays_to_date(self):
        self.assertEqual(
            get_window("quarter to date", shift_anchor(ANCHOR, "year", -1)),
            (getdate("2025-07-01"), getdate("2025-08-10")),
        )

    # @feature charts.number-period
    def test_an_unknown_unit_is_rejected(self):
        with self.assertRaises(Exception):
            shift_anchor(ANCHOR, "fortnight", -1)


class TestTimespanFilter(InsightsIntegrationTestCase):
    def compiled(self, timespan):
        expression = handle_timespan(sa_column("posting_date"), timespan)
        return str(expression.compile(compile_kwargs={"literal_binds": True}))

    # @feature query.filter-relative-date
    def test_a_to_date_span_filters_up_to_today(self):
        with patch(NOW, return_value="2026-08-10"):
            sql = self.compiled("Month to Date")
            self.assertIn("2026-08-01 00:00:00", sql)
            self.assertIn("2026-08-10 23:59:59", sql)

    # @feature settings.week-start
    def test_an_existing_span_is_unchanged(self):
        with self.change_settings("Insights Settings", week_starts_on="Monday"):
            with patch(NOW, return_value="2022-11-26"):
                sql = self.compiled("Current Week")
                self.assertIn("2022-11-21 00:00:00", sql)
                self.assertIn("2022-11-27 23:59:59", sql)

    # @feature query.filter-relative-date
    def test_a_span_given_as_a_list_is_joined(self):
        with patch(NOW, return_value="2022-11-26"):
            sql = self.compiled(["Last", "7", "Days"])
            self.assertIn("2022-11-19 00:00:00", sql)
            self.assertIn("2022-11-25 23:59:59", sql)

    # @feature query.filter-relative-date
    def test_a_span_given_as_a_list_with_a_number_in_it_is_joined(self):
        """The column header seeds the count as a number, not as its word."""
        with patch(NOW, return_value="2022-11-26"):
            sql = self.compiled(["Last", 1, "Day"])
            self.assertIn("2022-11-25 00:00:00", sql)
            self.assertIn("2022-11-25 23:59:59", sql)

    # @feature query.filter-relative-date
    def test_a_span_naming_no_count_reads_as_one_period(self):
        with patch(NOW, return_value="2022-11-26"):
            sql = self.compiled("Last Month")
            self.assertIn("2022-10-01 00:00:00", sql)
            self.assertIn("2022-10-31 23:59:59", sql)

    # @feature query.filter-relative-date-shift
    def test_a_span_can_pin_its_own_anchor(self):
        """A card that must read the same figure whenever it is opened."""
        with patch(NOW, return_value="2026-11-30"):
            sql = self.compiled({"span": "month to date", "anchor": "2026-08-10"})
            self.assertIn("2026-08-01 00:00:00", sql)
            self.assertIn("2026-08-10 23:59:59", sql)

    # @feature query.filter-relative-date-shift
    def test_a_shift_moves_the_anchor_and_the_span_is_measured_again(self):
        """The same ten days a fiscal year back, not the span's dates moved."""
        with self.change_settings("Insights Settings", fiscal_year_start="2020-04-01"):
            sql = self.compiled(
                {
                    "span": "month to date",
                    "anchor": "2026-08-10",
                    "shift": {"unit": "fiscal year", "count": -1},
                }
            )
            self.assertIn("2025-08-01 00:00:00", sql)
            self.assertIn("2025-08-10 23:59:59", sql)

    # @feature query.filter-relative-date-shift
    def test_a_shift_with_no_anchor_moves_today(self):
        with patch(NOW, return_value="2026-08-10"):
            sql = self.compiled({"span": "month to date", "shift": {"unit": "year", "count": -1}})
            self.assertIn("2025-08-01 00:00:00", sql)
            self.assertIn("2025-08-10 23:59:59", sql)

    # @feature query.filter-relative-date
    def test_a_value_naming_no_span_is_rejected(self):
        with self.assertRaises(Exception):
            self.compiled({"anchor": "2026-08-10"})


class TestDirectionalSpans(InsightsIntegrationTestCase):
    """N whole periods either side of the anchor's own, which is never one of them.

    The picker prints the same range under the row it filters by, so a span that
    counted its ends differently here would filter a span the reader was shown
    the opposite of.
    """

    def assert_ranges(self, expected, include_current=False):
        with self.change_settings(
            "Insights Settings", week_starts_on="Monday", fiscal_year_start="2020-04-01"
        ):
            for timespan, dates in expected.items():
                result = [get_date_str(d) for d in get_date_range(timespan, include_current, ANCHOR)]
                self.assertEqual(result, dates, timespan)

    # @feature query.filter-relative-date
    def test_a_forward_span_runs_from_the_next_period_to_the_nth(self):
        self.assert_ranges(
            {
                "next 3 day": ["2026-08-11", "2026-08-13"],
                "next 3 week": ["2026-08-17", "2026-09-06"],
                "next 3 month": ["2026-09-01", "2026-11-30"],
                "next 3 quarter": ["2026-10-01", "2027-06-30"],
                "next 3 year": ["2027-01-01", "2029-12-31"],
                "next 3 fiscal year": ["2027-04-01", "2030-03-31"],
            }
        )

    # @feature query.filter-relative-date
    def test_a_backward_span_runs_from_the_nth_period_to_the_previous(self):
        self.assert_ranges(
            {
                "last 3 day": ["2026-08-07", "2026-08-09"],
                "last 3 week": ["2026-07-20", "2026-08-09"],
                "last 3 month": ["2026-05-01", "2026-07-31"],
                "last 3 quarter": ["2025-10-01", "2026-06-30"],
                "last 3 year": ["2023-01-01", "2025-12-31"],
                "last 3 fiscal year": ["2023-04-01", "2026-03-31"],
            }
        )

    # @feature query.filter-relative-date
    def test_one_period_is_the_period_next_to_the_anchor(self):
        self.assert_ranges(
            {
                "next 1 month": ["2026-09-01", "2026-09-30"],
                "last 1 month": ["2026-07-01", "2026-07-31"],
                "next 1 fiscal year": ["2027-04-01", "2028-03-31"],
                "last 1 fiscal year": ["2025-04-01", "2026-03-31"],
            }
        )

    # @feature query.filter-relative-date-include-current
    def test_including_the_current_period_extends_the_near_end(self):
        self.assert_ranges(
            {
                "next 3 month": ["2026-08-01", "2026-11-30"],
                "last 3 month": ["2026-05-01", "2026-08-31"],
            },
            include_current=True,
        )
