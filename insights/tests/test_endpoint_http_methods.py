"""An endpoint that keeps a write under GET accepts only POST.

`InsightsIntegrationTestCase` watches every test for such an endpoint. These
tests pin what the watch reports.
"""

import frappe

from insights.decorators import insights_whitelist
from insights.tests.base import InsightsIntegrationTestCase


class GetWritesAreReported(InsightsIntegrationTestCase):
    # @feature permissions.get-keeps-no-write
    def test_an_endpoint_that_commits_under_get_is_reported(self):
        @insights_whitelist()
        def save_title(title: str):
            frappe.db.commit()  # nosemgrep - the write the watch looks for

        save_title(title="Sales")
        with self.assertRaisesRegex(AssertionError, "save_title commits but accepts GET"):
            self.assert_no_get_writes()

    # @feature permissions.get-keeps-no-write
    def test_an_endpoint_that_accepts_only_post_may_commit(self):
        @insights_whitelist(methods=["POST"])
        def save_title(title: str):
            frappe.db.commit()  # nosemgrep - the write the watch looks for

        save_title(title="Sales")
        self.assert_no_get_writes()
