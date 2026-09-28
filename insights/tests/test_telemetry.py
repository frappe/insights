"""Every event carries the app version and the site's entry cohort.

An analysis that reads a series by version or by cohort needs both properties on
every row. No answer is worth failing the action that reported it.
"""

from unittest.mock import patch

import frappe

import insights
from insights.telemetry import capture, get_entry, is_standard_app
from insights.tests.base import InsightsIntegrationTestCase


class TestTelemetryDefaults(InsightsIntegrationTestCase):
    def before_test(self):
        get_entry.clear_cache()
        self.addCleanup(get_entry.clear_cache)

    def sent(self, installed_apps=("frappe", "insights"), conf=None):
        """Return the call the framework's telemetry received."""
        with (
            patch("frappe.utils.telemetry.capture") as sender,
            patch("frappe.get_installed_apps", return_value=list(installed_apps)),
            patch.object(frappe, "conf", frappe._dict(conf or {})),
        ):
            capture("workbook_created", interval="1d", from_template=True)
        return sender.call_args

    # @feature telemetry.defaults
    def test_an_event_carries_the_app_version_and_the_entry_cohort(self):
        args, kwargs = self.sent()
        self.assertEqual(args, ("workbook_created", "insights"))
        self.assertEqual(kwargs["interval"], "1d")
        self.assertEqual(
            kwargs["properties"],
            {
                "app_version": insights.__version__,
                "entry": "self_hosted",
                "from_template": True,
            },
        )

    # @feature telemetry.defaults
    def test_a_site_running_erpnext_enters_as_an_erpnext_site(self):
        _, kwargs = self.sent(installed_apps=("frappe", "erpnext", "insights"))
        self.assertEqual(kwargs["properties"]["entry"], "erpnext_site")

    # @feature telemetry.defaults
    def test_a_frappe_cloud_site_without_erpnext_enters_as_a_trial(self):
        _, kwargs = self.sent(conf={"fc_team": "team@example.com"})
        self.assertEqual(kwargs["properties"]["entry"], "saas_trial")

    # @feature telemetry.defaults
    def test_erpnext_outranks_a_frappe_cloud_team(self):
        _, kwargs = self.sent(
            installed_apps=("frappe", "erpnext", "insights"), conf={"fc_team": "team@example.com"}
        )
        self.assertEqual(kwargs["properties"]["entry"], "erpnext_site")

    # @feature telemetry.standard-names-only
    def test_an_app_is_standard_only_when_its_publisher_is_frappe_itself(self):
        for publisher in (
            "Frappe Technologies",
            "Frappe Technologies Pvt. Ltd.",
            "Frappe Technologies Pvt Ltd",
            "  frappe technologies pvt ltd  ",
        ):
            with patch("frappe.get_hooks", return_value=[publisher]):
                self.assertTrue(is_standard_app("an_app"), publisher)

        for publisher in ("NotFrappe", "Frappe Technologies Fan Club", "Acme"):
            with patch("frappe.get_hooks", return_value=[publisher]):
                self.assertFalse(is_standard_app("an_app"), publisher)

    # @feature telemetry.defaults
    def test_a_refused_send_does_not_reach_the_caller(self):
        with patch("frappe.utils.telemetry.capture", side_effect=Exception("pulse is down")):
            capture("workbook_created")
