from unittest.mock import patch

from frappe.utils.data import get_date_str

from insights.insights.query_builders.sql_functions import get_date_range
from insights.tests.base import InsightsIntegrationTestCase

# 2022-11-26 is a Saturday
NOW = "insights.insights.query_builders.sql_functions.nowdate"

# timespans are already lowercased and singularised by handle_timespan


class TestWeekDateRanges(InsightsIntegrationTestCase):
    def assert_ranges(self, expected, include_current=False):
        with patch(NOW, return_value="2022-11-26"):
            for timespan, dates in expected.items():
                result = [get_date_str(d) for d in get_date_range(timespan, include_current)]
                self.assertEqual(result, dates, timespan)

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

    def test_include_current_extends_to_this_week(self):
        with self.change_settings("Insights Settings", week_starts_on="Monday"):
            self.assert_ranges(
                {
                    "last 1 week": ["2022-11-14", "2022-11-27"],
                    "next 1 week": ["2022-11-21", "2022-12-04"],
                },
                include_current=True,
            )
